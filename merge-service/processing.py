﻿import os
import subprocess

from config import getConfig
from utils import HTTPResponse, CacheFunction, fetchUrl, str2bool, ParameterExtractor
import traceback
from github import GitHub
from urllib2 import HTTPError

from pprint import pprint

class Repository():
    def __init__(self, repocfg):
        repocfg['_object'] = self
        self.cfg = repocfg

    class GitHubPullRequest():
        def __init__(self, repo, prId):
            self.repo = repo
            self.prId = prId
            self.assignee = None
            self.lastApproval = None
            self.lastApprovalReviews = None
            # GitHub API objects
            cfg = getConfig()
            self.apiClientPullrequest = GitHub(userAgent=cfg['userAgent'], reuseETag=True, access_token=cfg['githubAccessToken'])
            self.apiClientComments = GitHub(userAgent=cfg['userAgent'], reuseETag=True, access_token=cfg['githubAccessToken'])
            self.apiClientReviews = GitHub(userAgent=cfg['userAgent'], reuseETag=True, access_token=cfg['githubAccessToken'])
            self.apiClientExtraBranch = GitHub(userAgent=cfg['userAgent'], reuseETag=True, access_token=cfg['githubAccessToken'])
            self.apiClientExtraPullRequest = GitHub(userAgent=cfg['userAgent'], reuseETag=True, access_token=cfg['githubAccessToken'])
            self.extra = None

        @CacheFunction(30)
        def _isPullRequestApproved(self):
            warnings = None
            try:
                apiClient = self.apiClientPullrequest
                info = apiClient.repos(self.repo.cfg['github']).pulls(self.prId).get()
                if apiClient.status == 304:
                    print('Pullrequest #%s is not changed, previous result was: %s ...' % (self.prId, self.lastApproval or self.lastApprovalReviews))
                    info = self.info
                self.info = info
                self.head_user = self.info['head']['repo']['owner']['login']
                self.head_repo = self.info['head']['repo']['name']
                self.head_branch = self.info['head']['ref']
                try:
                    allowMultipleCommits = False
                    allowMultipleCommits_param = ParameterExtractor(self.info['body'] or '').extractParameterEx('allow_multiple_commits')
                    if allowMultipleCommits_param:
                        allowMultipleCommits = bool(allowMultipleCommits_param[1])
                        print('Process allow_multiple_commits=%s (%s)' % (allowMultipleCommits_param[1], allowMultipleCommits))
                    if not allowMultipleCommits and int(info.get('commits', 1)) > 1:
                        warnings = 'Multiple commits in this PR (allow_multiple_commits=1 to bypass this warning)'
                except:
                    traceback.print_exc()
                try:
                    if self.head_branch in ['master', '2.4', '3.4']:
                        self.extra = False
                    else:
                        extra_branch_parameter = ParameterExtractor(self.info['body'] or '').extractParameterEx('opencv_extra')
                        extra_branch_name = self.head_branch
                        if extra_branch_parameter:
                            extra_branch_name = extra_branch_parameter[1]
                        print('Query extra branch: %s/%s %s ...' % (self.head_user, 'opencv_extra', extra_branch_name))
                        apiClient = self.apiClientExtraBranch
                        extraBranch = apiClient.repos(self.head_user) \
                            ('opencv_extra') \
                            ('branches')(extra_branch_name).get()
                        if apiClient.status == 304:
                            print('Pullrequest #%s extra branch is not changed' % (self.prId))
                        elif apiClient.status == 404:
                            print('Pullrequest #%s extra branch is not found' % (self.prId))
                            self.extra = False
                        else:
                            self.extra = ('name' in extraBranch)
                        if self.extra:
                            self.extra_branch = extra_branch_name
                except:
                    traceback.print_exc()
                    self.extra = False
                print("Extra: %s" % self.extra)
                self.assignee = None
                if "assignee" in info and info['assignee'] != None:
                    self.assignee = info["assignee"]["login"]
                if self.assignee is None:
                    warnings = 'Pullrequest #%s is not assigned ...' % self.prId
                    print(warnings)
                    self.lastApproval = False
                    self.lastApprovalReviews = False
                    return (False, warnings)
                # Scan last updated comments
                apiClient = self.apiClientComments
                info = apiClient.repos(self.repo.cfg['github']).issues(self.prId).comments.get(sort='updated', direction='desc')
                if apiClient.status == 304:
                    print('Pullrequest #%s comments are not changed, use previous result: %s ...' % (self.prId, self.lastApproval))
                elif apiClient.status == 200:
                    # May be check only last updated comment ?
                    for comment in info:
                        if comment["user"]["login"] == self.assignee:
                            if ':shipit:' in comment["body"] or ':+1:' in comment["body"]:
                                print('Pullrequest #%s is approved via comments ...' % self.prId)
                                self.lastApproval = True
                                break
                if self.lastApproval:
                    return (True, warnings)

                apiClient = self.apiClientReviews
                info = apiClient.repos(self.repo.cfg['github']).pulls(self.prId).reviews.get()
                if apiClient.status == 304:
                    print('Pullrequest #%s reviews are not changed, use previous result: %s ...' % (self.prId, self.lastApprovalReviews))
                    lastApproval = self.lastApprovalReviews
                elif apiClient.status == 200:
                    for review in info:
                        if review["user"]["login"] == self.assignee:
                            if review["state"] == 'APPROVED':
                                print('Pullrequest #%s is approved via reviews ...' % self.prId)
                                self.lastApprovalReviews = True
                                break
                if self.lastApprovalReviews:
                    return (True, warnings)

                warnings = 'Pullrequest #%s is not approved ...' % self.prId
                print(warnings)
                return (False, warnings)
            except:
                traceback.print_exc()
                self.info = None
                self.lastApproval = False
                self.lastApprovalReviews = False
                return (False, "Internal error")

        @CacheFunction(10, initialCleanupThreshold=256)
        def isPullRequestBuildsOK(self, batch):
            try:
                print('Check builds for pullrequest #%s ...' % self.prId)
                checklist = self.repo.cfg['checklist']
                for (buildersName, buildersConfig) in checklist.items():
                    response = None
                    if batch:
                        url = buildersConfig['url_all']
                        try:
                            url_response = fetchUrl(url)
                            response = url_response['pullrequests'][str(self.prId)]
                        except HTTPError as e:
                            traceback.print_exc()
                            batch = False
                    if response is None:
                        url = buildersConfig['url'].format(prId=self.prId)
                        print(" Check %s via %s" % (buildersName, url))
                        # Valid statuses are: pending, success, error, failure or None
                        try:
                            response = fetchUrl(url)
                        except HTTPError as e:
                            traceback.print_exc()
                            return (False, "Can't check builds on %s" % buildersName)
                    buildstatuses = response['buildstatus']
                    requiredlist = buildersConfig['requiredlist']
                    optionalrunlist = buildersConfig.get('optionalrunlist', [])
                    errors = []
                    for b in requiredlist:
                        if not b in buildstatuses:
                            print('  No info about build configuration "%s" on "%s"' % (b, buildersName))
                            errors.append("Can't find build %s" % b)
                        elif buildstatuses[b]['status'] in ['not_queued']:
                            print('  Build configuration is in progress: "%s" on "%s"' % (b, buildersName))
                            errors.append("Waiting for builds")
                    for b in requiredlist + optionalrunlist:
                        if not b in buildstatuses:
                            continue
                        elif buildstatuses[b]['status'] != 'success':
                            if buildstatuses[b]['status'] in ['not_queued']:
                                pass
                            elif buildstatuses[b]['status'] in ['building', 'queued', 'scheduling', 'scheduled']:
                                print('  Build configuration is in progress: "%s" on "%s"' % (b, buildersName))
                                errors.append("Waiting for builds")
                            else:
                                print('  Unsuccessful build configuration "%s" on "%s"' % (b, buildersName))
                                errors.append("Unsuccessful builds")
                        elif int(buildstatuses[b]['last_update']) > 10*24*3600:
                            errors.append("Build %s is too old" % b)
                    if len(errors) > 0:
                        print(' Check failed on "%s"' % (buildersName))
                        return (False, '. '.join(list(set(errors))))
                return (True, "Required builds passed")
            except:
                traceback.print_exc()
                raise

        @CacheFunction(30)
        def getPullRequestExtra(self):
            try:
                if self.extra is False:
                    return
                apiClient = self.apiClientExtraPullRequest
                extraPRs = apiClient.repos(self.repo.cfg['extra_github']).pulls.get(state='open', per_page=100)
                if apiClient.status == 304:
                    print('Extra pullrequests are not changed')
                    extraPRs = self.extraPRs
                else:
                    self.extraPRs = extraPRs
                for pr in extraPRs:
                    try:
                        if not pr['head']['repo']:
                            continue
                        if self.head_user == pr['head']['repo']['owner']['login'] and \
                                'opencv_extra' == pr['head']['repo']['name'] and \
                                self.extra_branch == pr['head']['ref']:
                            return pr
                    except:
                        print("pr=")
                        pprint(pr)
                        traceback.print_exc()
                        pass # ignore broken pr
                return None
            except:
                traceback.print_exc()
                raise


        def isPullRequestReadyToMerge(self):
            warnings = []
            status, msg = self.isPullRequestBuildsOK(False)
            if status == True:
                status, msg = self._isPullRequestApproved()
                if msg:
                    warnings.append(msg)
                if status:
                    prExtra = None
                    if self.extra:
                        prExtra = self.getPullRequestExtra()
                        if prExtra is None:
                            return (False, 'PR is ready to merge, but PR for "extra" is not created')
                        else:
                            self.prIdExtra = prExtra['number']
                            try:
                                allowMultipleCommits = False
                                allowMultipleCommits_param = ParameterExtractor(self.info['body'] or '').extractParameterEx('allow_multiple_commits_extra')
                                if allowMultipleCommits_param:
                                    allowMultipleCommits = bool(allowMultipleCommits_param[1])
                                    print('Process allow_multiple_commits=%s (%s)' % (allowMultipleCommits_param[1], allowMultipleCommits))
                                if not allowMultipleCommits and int(pr.get('commits', 1)) > 1:
                                    warnings.append('Multiple commits in opencv_extra PR #%s (allow_multiple_commits_extra=1 to bypass this warning)' % self.prIdExtra)
                            except:
                                traceback.print_exc()
                    if len(warnings) > 0:
                        return (False, ' \n'.join(warnings))
                    return (True, 'Ready to merge (%s)' % (('with "extra" #%s' % self.prIdExtra) if self.extra else 'without "extra"'))

            return (status, msg)

        def configureMergeScriptEnvironment(self, env, author):
            def checkedParameter(v):
                if v is None:
                    raise Exception('Invalid parameter')
                v = str(v)
                if len(v) == 0:
                    raise Exception('Invalid parameter')
                return v

            env['MERGER_NAME'] = checkedParameter(author.split(",")[0])
            env['MERGER_EMAIL'] = checkedParameter(author.split(",")[1])

            env['MERGE_PR'] = checkedParameter(self.prId)
            env['MERGE_BRANCH'] = checkedParameter(self.info['base']['ref'])
            env['MERGE_BRANCH_FROM'] = checkedParameter("%s:%s" % (self.head_user, self.head_branch))
            env['MERGE_REPO_ABS'] = checkedParameter(self.repo.cfg['path'])

            if self.extra:
                env['MERGE_EXTRA_PR'] = checkedParameter(self.prIdExtra)
                env['MERGE_EXTRA_BRANCH'] = checkedParameter(self.info['base']['ref'])
                env['MERGE_EXTRA_BRANCH_FROM'] = checkedParameter("%s:%s" % (self.head_user, self.extra_branch))
                env['MERGE_EXTRA_AUTHOR'] = checkedParameter(author)
                env['MERGE_EXTRA_REPO_ABS'] = checkedParameter(self.repo.cfg['extra_path'])

    @CacheFunction(24 * 3600, initialCleanupThreshold=256)
    def getPullRequest(self, prId):
        if self.cfg['type'] == 'GitHub':
            return self.GitHubPullRequest(self, prId)
        raise Exception('Invalid service configuration')


def getRepo(repoId):
    # :rtype: Repository
    cfg = getConfig()['repositories']
    if repoId is None or not repoId in cfg:
        raise HTTPResponse(400, "Invalid repoId value")
    repocfg = cfg[repoId]
    if not '_object' in repocfg:
        repo = Repository(repocfg)
    else:
        repo = repocfg['_object']
    return repo


def checkMergeRight(httpHandler=None):
    if httpHandler:
        if hasattr(httpHandler, 'userRights'):
            if 'mergeRight' in httpHandler.userRights:
                return True
    return False


def getAuthInfo(httpHandler=None):
    res = {}
    if httpHandler:
        if hasattr(httpHandler, 'user'):
            res['user'] = httpHandler.user
        if hasattr(httpHandler, 'userRights'):
            if 'mergeRight' in httpHandler.userRights:
                res['mergeRight'] = True
    if not 'user' in res:
        return (200, dict(message='Not authorized'))
    return res

def getParameterValue(p):
    if isinstance(p, list):
        if len(p) != 1:
            return None
        p = p[0]
    return p

def doQuery(repoId=None, prId=None, httpHandler=None):
    repoId = getParameterValue(repoId)
    if repoId is None:
        raise HTTPResponse(400, "Invalid repoId parameter")

    prId = getParameterValue(prId)
    if prId is None:
        raise HTTPResponse(400, "Invalid prId parameter")

    repo = getRepo(repoId)

    if not 'checklist' in repo.cfg:
        raise HTTPResponse(400, "Can't check internal repository")

    pr = repo.getPullRequest(prId)
    res, message = pr.isPullRequestReadyToMerge()

    return (200, dict(status=res, message=message))

def doQueryFast(repoId=None, prId=None, httpHandler=None):
    repoId = getParameterValue(repoId)
    if repoId is None:
        raise HTTPResponse(400, "Invalid repoId parameter")

    repo = getRepo(repoId)
    if not 'checklist' in repo.cfg:
        raise HTTPResponse(400, "Can't check internal repository")

    if isinstance(prId, list) and len(prId) > 1:
        result = {}
        for pr in prId:
            pr_obj = repo.getPullRequest(pr)
            res, message = pr_obj.isPullRequestBuildsOK(True)
            result[pr] = dict(statusFast=res, messageFast=message)
        return (200, result)
    else:
        prId = getParameterValue(prId)
        if prId is None:
            raise HTTPResponse(400, "Invalid prId parameter")

        pr = repo.getPullRequest(prId)
        res, message = pr.isPullRequestBuildsOK(False)
        return (200, dict(statusFast=res, messageFast=message))


def doMerge(repoId=None, prId=None, httpHandler=None):
    if not checkMergeRight(httpHandler):
        raise HTTPResponse(403, "No rights to merge!")

    repoId = getParameterValue(repoId)
    if repoId is None:
        raise HTTPResponse(400, "Invalid repoId parameter")

    prId = getParameterValue(prId)
    if prId is None:
        raise HTTPResponse(400, "Invalid prId parameter")

    repo = getRepo(repoId)

    pr = repo.getPullRequest(prId)
    res, message = pr.isPullRequestReadyToMerge()

    if res != True:
        raise HTTPResponse(409, "Pull request is not ready to merge!")

    env = os.environ.copy()

    pr.configureMergeScriptEnvironment(env, httpHandler.userComment)

    baseDir = os.path.dirname(__file__)
    mergeScript = os.path.join(baseDir, repo.cfg['merge_script'])

    try:
        output = subprocess.check_output(['bash', '-c', mergeScript], env=env, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print e.output
        raise HTTPResponse(500, dict(message="Merge script failed", code=e.returncode, detail=e.output))
    except:
        traceback.print_exc()
        raise HTTPResponse(500, "Internal error")

    print output
    return dict(status=True, message='Merged!', detail=output)

#!/bin/bash -e

# Passed parameters:

# MERGER_NAME="Alexander Alekhin"
# MERGER_EMAIL="alexander.alekhin@itseez.com"

# MERGE_PR=2772
# MERGE_BRANCH=master
# MERGE_BRANCH_FROM=<user>:<branch>
# MERGE_REPO_ABS=/opt/repositories-merge/opencv

# MERGE_EXTRA_PR=184
# MERGE_EXTRA_BRANCH=master
# MERGE_EXTRA_BRANCH_FROM=<user>:<branch>
# MERGE_EXTRA_REPO_ABS=/opt/repositories-merge/opencv_extra


#echo "Merging is disabled (waiting for release tag merge)"
#exit 1

(
  # Wait for lock on
  flock -x -w 30 200 || exit 1

  # be care
  cd /tmp

  set -x

  if [ "${MERGE_EXTRA_PR}" ]; then
    pushd ${MERGE_EXTRA_REPO_ABS}

    git fetch --prune --verbose origin
    git reset --hard
    git clean -f -d -x
    git checkout --detach origin/${MERGE_EXTRA_BRANCH}
    git checkout -B ${MERGE_EXTRA_BRANCH} origin/${MERGE_EXTRA_BRANCH}
    git fetch --verbose upstream +refs/pull/${MERGE_EXTRA_PR}/head
    if [[ `git merge-base HEAD FETCH_HEAD` == `git rev-parse FETCH_HEAD` ]]; then
      echo "WARNING: Extra branch was already merged! Do nothing"
    else
      git merge --no-ff --no-edit --verbose FETCH_HEAD
      GIT_COMMITTER_NAME=${MERGER_NAME} GIT_COMMITTER_EMAIL=${MERGER_EMAIL} \
          git commit --amend --message "Merge pull request #${MERGE_EXTRA_PR} from ${MERGE_EXTRA_BRANCH_FROM}" --author="${MERGER_NAME} <${MERGER_EMAIL}>"
      git push --verbose upstream ${MERGE_EXTRA_BRANCH}
    fi

    popd

    echo ""
    echo "Extra merged!"
    echo ""
  fi

  if [ "${MERGE_PR}" ]; then
    pushd ${MERGE_REPO_ABS}

    git fetch --prune --verbose origin
    git reset --hard
    git clean -f -d -x
    git checkout --detach origin/${MERGE_BRANCH}
    git checkout -B ${MERGE_BRANCH} origin/${MERGE_BRANCH}
    git fetch --verbose upstream +refs/pull/${MERGE_PR}/head
    if [[ `git merge-base HEAD FETCH_HEAD` == `git rev-parse FETCH_HEAD` ]]; then
      echo "WARNING: Branch was already merged! Do nothing"
    else
      git merge --no-ff --no-edit --verbose FETCH_HEAD
      GIT_COMMITTER_NAME=${MERGER_NAME} GIT_COMMITTER_EMAIL=${MERGER_EMAIL} \
          git commit --amend --message "Merge pull request #${MERGE_PR} from ${MERGE_BRANCH_FROM}" --author="${MERGER_NAME} <${MERGER_EMAIL}>"
      git push --verbose upstream ${MERGE_BRANCH}
    fi

    popd
  fi

) 200>/tmp/merge.exclusivelock

from __future__ import print_function

import base64
import cgi
import mimetypes
import os
import posixpath
import shutil
import sys
import traceback
import urlparse

from pprint import pprint
from BaseHTTPServer import BaseHTTPRequestHandler

from processing import doMerge, doQuery, doQueryFast, checkMergeRight, getAuthInfo
from utils import cacheFileAccess, HTTPResponse
import json

get_routes = {
        '/checkMergeRight': checkMergeRight,
        '/authInfo': getAuthInfo,
        '/queryFast' : doQueryFast,
        }

post_routes = {
        '/merge' : doMerge,
        '/query' : doQuery,
        }

extensions_map = mimetypes.types_map.copy()
extensions_map.update({
    '': 'application/octet-stream',  # Default
    '.py': 'text/plain',
    '.c': 'text/plain',
    '.h': 'text/plain',
})

def get_ctype(path):
    _, ext = posixpath.splitext(path)
    if extensions_map.has_key(ext):
        return extensions_map[ext]
    ext = ext.lower()
    if extensions_map.has_key(ext):
        return extensions_map[ext]
    else:
        return extensions_map['']


@cacheFileAccess
def getHTPASSWD(fileName):
    print('Loading htpasswd file: %s' % fileName)
    with open(fileName, "r") as f:
        lines = f.readlines()
    lines = [l.rstrip().split(':', 3)  # user:password hash:comment:rights
             for l in lines if len(l) > 0 and not l.startswith('#')]
    return lines

def validatePassword(passwd, pwhash):
    from crypt import crypt
    if pwhash == crypt(passwd, pwhash[0:2]):
        return True
    if len(pwhash) > 12 and pwhash == crypt(passwd, pwhash[0:12]):
        return True
    return False
    
class Handler(BaseHTTPRequestHandler):

    def parse_request(self):
        if not BaseHTTPRequestHandler.parse_request(self):
            return False

        header = self.headers.get('Authorization', '')
        if header:
            scheme, data = header.split()
            if scheme != 'Basic':
                self.send_error(501)
                return False
            data = base64.decodestring(data)
            user, pw = data.split(':', 2)
            if self.get_userinfo(user, pw, self.command):
                return True
            else:
                self.send_autherror(401, "Invalid user/password")
                return False

        if self.command != 'GET':        
            self.send_autherror(401, "Authorization Required")
        else:
            return True


    def get_userinfo(self, user, pw, command=''):
        try:
            lines = getHTPASSWD(os.path.join(os.path.dirname(__file__), '../htpasswd'))
            lines = [l for l in lines if l[0] == user]
            if not lines:
                return False
            l = lines[0]
            pwhash = l[1]
            res = validatePassword(pw, pwhash)
            if res:
                self.user = user
                self.userComment = l[2] if len(l) > 2 else None
                self.userRights = l[3].split(",") if len(l) > 3 else []
            return res
        except:
            print(traceback.format_exc())
            print(sys.exc_info()[0])
            return False

    def send_autherror(self, code, message=None):
        emsg = """\
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<HTML><HEAD>
<TITLE>401 Authorization Required</TITLE>
</HEAD><BODY>
<H1>Authorization Required</H1>
This server could not verify that you
are authorized.  Either you supplied the wrong
credentials (e.g., bad password), or your
browser doesn't understand how to supply
the credentials required.<P>
</BODY></HTML>"""
        self.log_error("code %d, message: %s", code, message)
        self.send_response(code, message)
        self.send_header("WWW-Authenticate", 'Basic realm="OpenCV CI"')
        self.send_header("Content-Type", 'text/html')
        self.end_headers()

        lines = emsg.split("\n")
        for l in lines:
            self.wfile.write("%s\r\n" % l)

    def do_GET(self):
        urlparts = urlparse.urlparse(self.path)
        pprint(urlparts)

        result = None
        resultCode = 200
        try:
            params = urlparse.parse_qs(urlparts.query)
            pprint(params)

            if urlparts.path in get_routes:
                result = get_routes[urlparts.path](httpHandler=self, **params)
                if isinstance(result, tuple):
                    resultCode, result = result
        except HTTPResponse as r:
            resultCode = r.status
            result = r.message
        except:
            print(traceback.format_exc())
            print(sys.exc_info()[0])
            self.send_response(500)
            self.end_headers()
            return

        if result is not None:
            ctype = 'text/html'
            if isinstance(result, str) and result.find('html') < 0:
                result = dict(message=result)
            if not isinstance(result, str):                
                ctype = 'application/json'
                if not isinstance(result, (dict, list)):
                    result = json.dumps([result])
                else:
                    result = json.dumps(result)
            self.send_response(resultCode)
            self.send_header("Content-type", "%s; charset=utf-8" % ctype)
            self.end_headers()
            self.wfile.write(result)
            if result[-2:] != '\r\n':
                self.wfile.write('\r\n')
        else:
            self.send_response(404)
            self.end_headers()

    
    def do_POST(self):
        urlparts = urlparse.urlparse(self.path)
        pprint(urlparts)
            
        result = None
        resultCode = 200
        try:
            if urlparts.query != '':
                return 403
            
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'application/json':
                length = int(self.headers.getheader('content-length'))
                params = json.loads(self.rfile.read(length))
            elif ctype == 'multipart/form-data':
                params = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers.getheader('content-length'))
                params = urlparse.parse_qs(self.rfile.read(length), keep_blank_values=1)
            else:
                params = {}

            if urlparts.path in post_routes:
                result = post_routes[urlparts.path](httpHandler=self, **params)
                if isinstance(result, tuple):
                    resultCode, result = result
        except HTTPResponse as r:
            resultCode = r.status
            result = r.message
        except:
            print(traceback.format_exc())
            print(sys.exc_info()[0])
            self.send_response(500)
            self.end_headers()
            return

        if result is not None:
            ctype = 'text/html'
            if isinstance(result, str) and result.find('html') < 0:
                result = dict(message=result)
            if not isinstance(result, str):                
                ctype = 'application/json'
                if not isinstance(result, (dict, list)):
                    result = json.dumps([result])
                else:
                    result = json.dumps(result)
            self.send_response(resultCode)
            self.send_header("Content-type", "%s; charset=utf-8" % ctype)
            self.end_headers()
            self.wfile.write(result)
            if result[-2:] != '\r\n':
                self.wfile.write('\r\n')
        else:
            self.send_response(403)
            self.end_headers()

    def do_DELETE(self):
        self.send_response(403)
        pass

    def do_PATCH(self):
        self.send_response(403)
        pass

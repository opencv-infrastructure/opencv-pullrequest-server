#!/usr/bin/env python
# encoding: utf-8
'''
Pull requests processing processing

@author:     Alexander Alekhin
            
@copyright:  2014 Itseez. All rights reserved.
            
@contact:    alexander.alekhin@itseez.com
'''

import sys
import os

from optparse import OptionParser

from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer

import sys, os
sys.path.append(os.path.abspath(os.path.dirname(__file__)) + '/api_github')

from webhandler import Handler

__all__ = []
__version__ = '0.1'
__date__ = '2014-04-24'
__updated__ = '2014-04-24'

DEBUG = 1
TESTRUN = 0
PROFILE = 0
VERBOSE = 0

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = 'v%s' % __version__
    program_build_date = '%s' % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_longdesc = ''''''  # optional - give further explanation about what the program does
    program_license = 'Copyright 2014 Itseez'

    if argv is None:
        argv = sys.argv[1:]
    try:
        # setup option parser
        parser = OptionParser(version=program_version_string, epilog=program_longdesc, description=program_license)
        parser.add_option("", "--addr", dest="addr", help="set listening addr [default: %default]")
        parser.add_option("-p", "--port", dest="addr", help="set listening port [default: %default]")
        parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")

        # set defaults
        global VERBOSE
        parser.set_defaults(addr='127.0.0.1', port=8008, verbose=VERBOSE)

        # process options
        (opts, _) = parser.parse_args(argv)

        if opts.verbose > 0:
            print("verbosity level = %d" % opts.verbose)
            VERBOSE = opts.verbose

        sys.stderr = sys.stdout # Redirect stderr to stdout

        print('Starting server at %s:%d' % (opts.addr, opts.port))
        #httpd = ThreadedHTTPServer((opts.addr, opts.port), Handler)
        httpd = HTTPServer((opts.addr, opts.port), Handler)
        httpd.serve_forever()

    except Exception, e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        raise
        return 2


if __name__ == "__main__":
    if DEBUG:
        pass
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'webserver_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())
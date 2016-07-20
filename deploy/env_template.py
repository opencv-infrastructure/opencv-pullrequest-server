#!/usr/bin/env python
import os, sys, jinja2
print(jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        .from_string(open(sys.argv[1], "r").read())
        .render(env=os.environ))

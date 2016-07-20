import json
import os
import sys
import jinja2

from utils import cacheFileAccess

DEBUG = getattr(sys.modules['__main__'], 'DEBUG', False)

@cacheFileAccess
def _readConfig(fileName):
    print('Loading config file: %s' % fileName)
    with open(fileName, "r") as f:
        file_content = f.read()
        template = jinja2.Environment().from_string(file_content)
        processed_content = template.render(env=os.environ)
        return json.loads(processed_content)
    
def getConfig():
    return _readConfig(os.path.join(os.path.dirname(__file__), '../config.json'))

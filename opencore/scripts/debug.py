""" Run an interactive debugging session  """

from code import interact
import os
import sys
from opencore.scripting import get_default_config
from opencore.scripting import open_root

import logging
logging.basicConfig()

def main(argv=sys.argv):
    config = None
    script = None
    if '-C' in argv:
        index = argv.index('-C')
        argv.pop(index)
        config = argv.pop(index)
    if len(argv) > 1:
        script = argv[1]
    if not config:
        config = get_default_config()
    root, closer = open_root(config)

    if script is None:
        cprt = ('Type "help" for more information. "root" is the openhcd '
                'root object.')
        banner = "Python %s on %s\n%s" % (sys.version, sys.platform, cprt)
        interact(banner, local={'root':root})
    else:
        code = compile(open(script).read(), script, 'exec')
        exec code in {'root': root}

if __name__ == '__main__':
    main()

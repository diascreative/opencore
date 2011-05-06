""" Rename a user. """

from opencore.scripting import get_default_config
from opencore.scripting import open_root
from opencore.utilities.rename_user import rename_user
from optparse import OptionParser
import sys
import transaction

import logging
logging.basicConfig()

def main():
    parser = OptionParser(description=__doc__,
                          usage="%prog [options] old_name new_name")

    parser.add_option('-C', '--config', dest='config', default=None,
        help="Specify a paster config file. Defaults to $CWD/etc/openhcd.ini")
    parser.add_option('-d', '--dry-run', dest='dry_run',
        action="store_true", default=False,
        help="Don't commit the transactions")
    parser.add_option('-M', '--merge', dest='merge', action='store_true',
                      default=False, help='Merge with an existing user.')

    options, args = parser.parse_args()
    if len(args) < 2:
        parser.error("Too few parameters: %s" % repr(args))
    if len(args) > 2:
        parser.error("Too many parameters: %s" % repr(args))

    config = options.config
    if config is None:
        config = get_default_config()
    root, closer = open_root(config)

    old_name, new_name = args
    rename_user(root, old_name, new_name, options.merge, sys.stdout)

    if options.dry_run:
        transaction.abort()
    else:
        transaction.commit()

if __name__ == '__main__':
    main()

""" Adds admin groups to the specified users
"""

import sys
import transaction
import optparse
import logging

from opencore.scripting import get_default_config
from opencore.scripting import open_root

ADMIN_GROUPS = ('group.KarlAdmin', 'group.KarlUserAdmin')

log = logging.getLogger(__name__)

def make_admin_user(users, userid):
    if users.get(userid) is not None:
        for group in ADMIN_GROUPS:
            users.add_group(userid, group)
        log.info('Added admin groups for: %s' % userid)
    else:
        log.info('Could not find user in database: %s' % userid)

def main(open_root=open_root, argv=sys.argv):
    parser = optparse.OptionParser(description=__doc__)
    parser.add_option('--dry-run', dest='dryrun',
        action='store_true', default=False,
        help="Don't actually commit the transaction")
    options, args = parser.parse_args(argv[1:])
    if len(args) < 1:
        log.error('Please specify the users you wish to make admins')
        return
    
    config = get_default_config()
    root, closer = open_root(config)

    users = root.users
    
    for userid in args:
        make_admin_user(users, userid)

    if not options.dryrun:
        transaction.commit()
    else: #pragma NO COVERAGE
        transaction.abort()

if __name__ == '__main__': #pragma NO COVERAGE
    main()
    

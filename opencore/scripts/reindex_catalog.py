""" Reindex the catalog  """

from openhcd.scripting import get_default_config
from openhcd.scripting import open_root
from opencore.models.catalog import reindex_catalog
from optparse import OptionParser
import re

def main():
    parser = OptionParser(description=__doc__)
    parser.add_option('-C', '--config', dest='config', default=None,
        help="Specify a paster config file. Defaults to $CWD/etc/karl.ini")
    parser.add_option('-d', '--dry-run', dest='dry_run',
        action="store_true", default=False,
        help="Don't commit the transactions")
    parser.add_option('-i', '--interval', dest='commit_interval',
        action="store", default=200,
        help="Commit every N transactions")
    parser.add_option('-p', '--path', dest='path',
        action="store", default=None, metavar='EXPR',
        help="Reindex only objects whose path matches a regular expression")
    parser.add_option('-n', '--index', dest='indexes',
        action="append", help="Reindex only the given index (can be repeated)")

    options, args = parser.parse_args()
    if args:
        parser.error("Too many parameters: %s" % repr(args))

    commit_interval = int(options.commit_interval)
    if options.path:
        path_re = re.compile(options.path)
    else:
        path_re = None

    config = options.config
    if config is None:
        config = get_default_config()
    root, closer = open_root(config)

    def output(msg):
        print msg

    kw = {}
    if options.indexes:
        kw['indexes'] = options.indexes

    reindex_catalog(root, path_re=path_re, commit_interval=commit_interval,
                    dry_run=options.dry_run, output=output, **kw)

if __name__ == '__main__':
    main()

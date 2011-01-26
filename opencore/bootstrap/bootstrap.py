import sys
import transaction
from zope.component import queryUtility
from zope.interface import alsoProvides

from repoze.bfg.traversal import model_path
from repoze.bfg import testing
from repoze.lemonade.content import create_content

from opencore.bootstrap.interfaces import IInitialData
from opencore.bootstrap.data import DefaultInitialData
from opencore.contentfeeds import SiteEvents
from opencore.interfaces import IProfile
from opencore.site import Site

def populate(root, do_transaction_begin=True):
    if do_transaction_begin:
        transaction.begin()
  
    data = queryUtility(IInitialData, default=DefaultInitialData())
    if 'communities_name' in dir(data):
        communities_name = data.communities_name
    else:
        communities_name = None 
    site = root['site'] = Site(communities_name)
    site.__acl__ = data.site_acl
    site.events = SiteEvents()

    # If a catalog database exists and does not already contain a catalog,
    # put the site-wide catalog in the catalog database.
    main_conn = root._p_jar
    try:
        catalog_conn = main_conn.get_connection('catalog')
    except KeyError:
        # No catalog connection defined.  Put the catalog in the
        # main database.
        pass
    else:
        catalog_root = catalog_conn.root()
        if 'catalog' not in catalog_root:
            catalog_root['catalog'] = site.catalog
            catalog_conn.add(site.catalog)
            main_conn.add(site)

    # the ZODB root isn't a Folder, so it doesn't send events that
    # would cause the root Site to be indexed
    docid = site.catalog.document_map.add(model_path(site))
    site.catalog.index_doc(docid, site)
    site.docid = docid

    # the staff_acl is the ACL used as a basis for "public" resources
    site.staff_acl = data.staff_acl

    site['profiles'].__acl__ = data.profiles_acl

    site.moderator_principals = data.moderator_principals
    site.member_principals = data.member_principals
    site.guest_principals = data.guest_principals

    profiles = site['profiles']

    users = site.users

    for login, firstname, lastname, email, groups in data.users_and_groups:
        users.add(login, login, login, groups)
        profile = profiles[login] = create_content(IProfile,
                                                   firstname=firstname,
                                                   lastname=lastname,
                                                   email=email,
                                                  )

    # tool factory wants a dummy request
    COMMUNIITY_INCLUDED_TOOLS = data.community_tools
    class FauxPost(dict):
        def getall(self, key):
            return self.get(key, ())
    request = testing.DummyRequest()
    request.environ['repoze.who.identity'] = {
            'repoze.who.userid': data.admin_user,
            'groups': data.admin_groups,
           }

    # Create a Default community
    request.POST = FauxPost(request.POST)
    converted = {}
    converted['title'] = 'default'
    converted['description'] = 'Created by startup script'
    converted['text'] = '<p>Default <em>values</em> in here.</p>'
    converted['security_state'] = 'public'
    converted['tags'] = ''
    converted['tools'] = COMMUNIITY_INCLUDED_TOOLS

    communities = site[communities_name]
    #add_community = AddCommunityFormController(communities, request)
    #add_community.handle_submit(converted)
    #communities['default'].title = 'Default Community'

 
    # Set up default feeds from snapshots.
    #import os
    #import feedparser
    #from karl.models.interfaces import IFeedsContainer
    #from karl.models.interfaces import IFeed
    #feeds_container = create_content(IFeedsContainer)
    #site['feeds'] = feeds_container
    #snapshot_dir = os.path.join(os.path.dirname(data.__file__), 'feedsnapshots')
    #for name in os.listdir(snapshot_dir):
        #feed_name, ext = os.path.splitext(name)
        #if ext != '.xml':
            #continue
        #path = os.path.abspath(os.path.join(snapshot_dir, name))
        #parser = feedparser.parse(path)
        #feed = create_content(IFeed, feed_name)
        #feed.update(parser)
        #feeds_container[feed_name] = feed

    bootstrap_evolution(root)

def bootstrap_evolution(root):
    from zope.component import getUtilitiesFor
    from repoze.evolution import IEvolutionManager
    for pkg_name, factory in getUtilitiesFor(IEvolutionManager):
        __import__(pkg_name)
        package = sys.modules[pkg_name]
        manager = factory(root, pkg_name, package.VERSION)
        # when we do start_over, we unconditionally set the database's
        # version number to the current code number
        manager._set_db_version(package.VERSION)

import sys
import transaction
from zope.component import queryUtility

from repoze.bfg.traversal import model_path
from repoze.lemonade.content import create_content

from opencore.bootstrap.interfaces import IInitialData
from opencore.bootstrap.data import DefaultInitialData
from opencore.models.contentfeeds import SiteEvents
from opencore.models.interfaces import IProfile
from opencore.models.site import Site
from opencore.security.policy import to_profile_active
import logging

log = logging.getLogger(__name__)

def populate(root, do_transaction_begin=True, post_app_setup=None):
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
        log.info('adding to users login=%s, groups=%s' % (login, str(groups)))
        users.add(login, login, login, groups)
        profile = profiles[login] = create_content(IProfile,
                                         firstname=firstname,
                                         lastname=lastname,
                                         email=email,
                                         )
        log.info('activating profile (%s)' % login)
        to_profile_active(profile)
        
        
    def noop_post_app_setup(site):
        log.info('no post app setup required.')
        return root
    
    post_app_setup_hook = post_app_setup or noop_post_app_setup
    post_app_setup_hook(site)
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

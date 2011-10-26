# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz.org
#               2010-2011 Large Blue
#               Fergus Doyle: fergus.doyle@largeblue.com
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


# stdlib
import sys
import logging
import transaction

# Zope
from zope.component import queryUtility

# Repoze
from repoze.bfg.traversal import model_path
from repoze.folder import Folder
from repoze.lemonade.content import create_content

# opencore
from opencore.bootstrap.interfaces import IInitialData
from opencore.bootstrap.data import DefaultInitialData
from opencore.models.contentfeeds import SiteEvents
from opencore.models.interfaces import IProfile, IStaticPage
from opencore.models.site import Site
from opencore.security.policy import to_profile_active
from opencore.views.utils import create_user_mboxes

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
    
    site['mailboxes'] = Folder()

    for login, firstname, lastname, email, groups in data.users_and_groups:
        log.info('adding to users login=%s, groups=%s' % (login, str(groups)))
        users.add(login, login, login, groups)
        profile = profiles[login] = create_content(IProfile,
                                         firstname=firstname,
                                         lastname=lastname,
                                         email=email,
                                         )
        to_profile_active(profile)
        create_user_mboxes(profile)

    def noop_post_app_setup(site):
        log.info('no post app setup required.')
        return root

    post_app_setup_hook = post_app_setup or noop_post_app_setup
    post_app_setup_hook(site)
    bootstrap_evolution(root)

    # Static pages.
    bootstrap_static_pages(site)

    site['reset_password'] = Folder()

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


def bootstrap_static_pages(site):
    # Static Pages; FAQ/about/legal etc.
    for title in DefaultInitialData.initial_static_titles:
        bootstrap_static_page(site, title)

def bootstrap_translations_page(site):
    page = create_content(IStaticPage,
            title='Download PDF', 
            text='''
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
            ''',
            description='''
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
''',

            creator=DefaultInitialData.admin_user,
            )
    page.template = 'translations.pt'
    site['toolkit']['en']['translations'] = page

def bootstrap_static_page(site, title):
    auto_gen = DefaultInitialData.initial_static_content_auto_generated
    text = title + ' - ' + auto_gen
    page = create_content(IStaticPage,
            title=title, 
            text=text,
            description=auto_gen.capitalize(),
            creator=DefaultInitialData.admin_user,
            )

    page_path = title.lower()
    try:
        site[page_path] = page
    except ValueError:
        # Silence out /src/opencore/opencore/models/contentfeeds.py, line 145, in _getInfo
        # trying to get the newly created page's content type.
        pass

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

from datetime import datetime
from zope.component import queryUtility
from zope.interface import implements

from repoze.bfg.security import Allow
from repoze.bfg.security import Authenticated

from opencore.bootstrap.interfaces import IInitialData

from opencore.security.policy import ADMINISTRATOR_PERMS
from opencore.security.policy import GUEST_PERMS
from opencore.security.policy import MEMBER_PERMS
from opencore.security.policy import MODERATOR_PERMS
from opencore.security.policy import API_PERMS

_marker = object()

class DefaultInitialData(object):
    implements(IInitialData)

    moderator_principals = ['group.KarlModerator']
    member_principals = ['group.KarlStaff']
    guest_principals = []
    community_tools = ('blog', 'wiki', 'calendar', 'files')
    intranet_tools = ('forums', 'intranets', 'files')
    admin_user = 'admin'
    admin_groups = ('group.KarlStaff', 'group.KarlAdmin')

    folder_markers = [
        ('network-news', 'Network News', 'network_news', 'files'),
        ('network-events', 'Network Events', 'network_events', 'files'),
    ]

    site_acl = [
        (Allow, Authenticated, GUEST_PERMS),
        (Allow, 'group.KarlStaff', MEMBER_PERMS),
        (Allow, 'group.KarlModerator', MODERATOR_PERMS),
        (Allow, 'group.KarlAdmin', ADMINISTRATOR_PERMS),
        (Allow, 'group.API', API_PERMS),
    ]

    profiles_acl = [
        (Allow, 'group.KarlUserAdmin', ADMINISTRATOR_PERMS),
        ]

    staff_acl = [
        (Allow, 'group.KarlAdmin', ADMINISTRATOR_PERMS+MODERATOR_PERMS),
        (Allow, 'group.KarlModerator', MODERATOR_PERMS),
        (Allow, 'group.KarlStaff', GUEST_PERMS)
        ]

    users_and_groups = [
        ('admin', 'Ad','Min','admin@example.com',
         ('group.KarlAdmin', 'group.KarlUserAdmin', 'group.KarlStaff')),
        ('api', 'API', 'User', 'api@example.com', ('group.API',)),
    ]

    initial_static_titles = ('Funding', 'FAQ', 'About', 'Contact',
            'Microgrants', 'Translations')
    initial_static_content_auto_generated = 'auto-generated by bootstrap'
    initial_site_announcement = {
            'text': '''Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat
non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.''',
            'timestamp': datetime.now(),
            'userid': 'admin',
            }

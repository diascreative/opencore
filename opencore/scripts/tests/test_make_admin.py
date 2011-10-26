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

import unittest
from repoze.bfg import testing
from testfixtures import LogCapture

class TestMakeAdmin(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        self.log = LogCapture()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, users, userid):
        from opencore.scripts.make_admin import make_admin_user
        return make_admin_user(users, userid)

    def test_make_site_admin(self):
        users = DummyUsers({'admin':testing.DummyModel()})

        self.assertEqual(users.groups.get('admin', []), [],
                         'admin user should have no groups to start with')

        self._callFUT(users, 'admin')
        from opencore.scripts.make_admin import ADMIN_GROUPS
        self.assertEqual(users.groups['admin'], list(ADMIN_GROUPS),
                         'admin user should have been updated with admin groups')
            
    def test_invalid_user(self):
        users = DummyUsers() # empty
        
        self._callFUT(users, 'invalid_user')
        self.assertEqual(users.keys(), [],
                         'no groups should have been added')
        
    
class TestScript(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        self.root = testing.DummyModel()
        self.log = LogCapture()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, *args):
        from opencore.scripts.make_admin import main
        def open_root(config):
            return self.root, lambda: None
        return main(open_root, list(args))
    
    def test_make_site_admin(self):
        users = DummyUsers({'admin':testing.DummyModel()})
        self.root.users = users
        self.assertEqual(users.groups.get('admin', []), [],
                         'admin user should have no groups to start with')

        self._callFUT('/path/to/script', 'admin')
        from opencore.scripts.make_admin import ADMIN_GROUPS
        self.assertEqual(users.groups['admin'], list(ADMIN_GROUPS),
                         'admin user should have been updated with admin groups')
        
    def test_no_args(self):
        try:
            self._callFUT('/path/to/script')
        except SystemExit, e:
            self.assertEqual(str(e), '2')
        
        
    
class DummyUsers(dict):
    def __init__(self, *args, **kw):
        super(DummyUsers, self).__init__(*args, **kw)
        self.groups = {}
    
    def add_group(self, userid, group):
        self.groups[userid] = self.groups.get(userid, []) + [group]
        

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
        

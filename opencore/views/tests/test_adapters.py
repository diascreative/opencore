import unittest
from repoze.bfg import testing

class TestProfileDict(unittest.TestCase):

    def setUp(self):
        self.config = testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _registerAdapters(self):
        from opencore.views.adapters import ProfileDict
        self.config.registry.registerAdapter(ProfileDict)

    def _callFUT(self, context, request):
        from opencore.views.interfaces import IAPIDict
        a = self.config.registry.queryMultiAdapter((context, request),
                                                   IAPIDict)
        return a

    def test_it(self):
        self._registerAdapters()

        from datetime import datetime
        from opencore.testing import DummyProfile
        from opencore.views.tests import DummyAPI
        context = DummyProfile(websites=[],
                               created=datetime.now(),
                               last_login_time=datetime.now()
                               )
        api = DummyAPI()
        api.static_url='http://example.com'
        request = testing.DummyRequest(api=api)

        a = self._callFUT(context, request)
        self.assertNotEqual(a, None)

        self.assertEqual(a['firstname'], context.firstname)
        self.assertEqual(a['firstname'], context.firstname)
        self.assertEqual(a['firstname'], context.firstname)
        self.assertEqual(a['firstname'], context.firstname)


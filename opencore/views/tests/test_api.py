
# stdlib
import unittest, uuid

# Repoze
from repoze.bfg import testing

# opencore
from opencore.views.api import TemplateAPI

class TestAPI(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

        
    def test_user_is_staff_is_iterable(self):
        environ={'repoze.who.identity':{uuid.uuid4().hex:uuid.uuid4().hex}}
        request = testing.DummyRequest(environ=environ)
        
        api = TemplateAPI(None, request, None)
        
        # Should return False which is fine because the whole point is to
        # actually make sure the whatever API's self._identity returns
        # is a dictionary.
        self.assertEquals(api.user_is_staff, False)
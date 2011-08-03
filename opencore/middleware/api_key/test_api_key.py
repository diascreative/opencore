import unittest
from repoze.bfg import testing
from opencore.middleware.api_key import make_plugin
class TestAPIKey(unittest.TestCase):

    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _create_plugin(self, keys='one, two, three'):
        return make_plugin('key', keys=keys, user_name='api')

    def test_good_key(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : "key=one&something=2"})
        self.assertEqual(result['repoze.who.userid'], 'api')

    def test_good_key_in_set_of_one(self):
        plugin = self._create_plugin('a')
        result = plugin.identify({'QUERY_STRING' : "key=a&something=2"})
        self.assertEqual(result['repoze.who.userid'], 'api')

    def test_bad_key(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : "key=xxx&something=2"})
        self.assertTrue(result is None)

    def test_missing_key(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : "something=2"})
        self.assertTrue(result is None)

    def test_no_query_string(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : None})
        self.assertTrue(result is None)

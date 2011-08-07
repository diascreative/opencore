import unittest
from repoze.bfg import testing

class TestDataView(unittest.TestCase):

    def setUp(self):
        self.config = testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.json_api import data_json
        return data_json(context, request)

    def test_unsupported_content_type(self):
        from opencore.views.tests import DummyAPI
        context = testing.DummyModel()
        api = DummyAPI()
        request = testing.DummyRequest(api=api)

        from webob.exc import HTTPNotFound
        self.assertRaises(HTTPNotFound, self._callFUT,
                          context, request)

    def test_supported_content_type(self):
        from opencore.views.tests import DummyAPI
        from opencore.testing import DummyProfile
        from opencore.views.adapters import ProfileDict
        self.config.registry.registerAdapter(ProfileDict)

        context = DummyProfile()
        api = DummyAPI()
        api.static_url = 'http://example.com'
        request = testing.DummyRequest(api=api)

        res = self._callFUT(context, request)
        self.assertEqual(res['item'], ProfileDict(context, request))


class TestListView(unittest.TestCase):

    def setUp(self):
        self.config = testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.json_api import list_json
        return list_json(context, request)

    def test_unsupported_content_type(self):
        from opencore.views.tests import DummyAPI
        context = testing.DummyModel()
        context['child1'] = testing.DummyModel()
        api = DummyAPI()
        request = testing.DummyRequest(api=api)

        res = self._callFUT(context, request)

        self.assertEqual(res['items'], [])

    def test_supported_content_type(self):
        from opencore.views.tests import DummyAPI
        from opencore.testing import DummyProfile
        from opencore.views.adapters import ProfileDict

        context = testing.DummyModel()
        context['child1'] = DummyProfile()
        api = DummyAPI()
        api.static_url = 'http://example.com'
        request = testing.DummyRequest(api=api)

        res = self._callFUT(context, request)

        self.assertEqual(res['items'], [])


        self.config.registry.registerAdapter(ProfileDict)

        res = self._callFUT(context, request)

        self.assertEqual(res['items'], [ProfileDict(context['child1'], request)])


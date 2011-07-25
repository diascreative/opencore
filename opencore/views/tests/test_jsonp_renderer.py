import unittest
from repoze.bfg import testing

class Test_jsonp_renderer_factory(unittest.TestCase):
    def _callFUT(self, name):
        from opencore.views.renderers import jsonp_renderer_factory
        return jsonp_renderer_factory(name)

    def test_with_request_content_type_notset(self):
        request = testing.DummyRequest()
        renderer = self._callFUT('foo.jsonp')
        renderer({'a':1}, {'request':request})
        self.assertEqual(request.response_content_type, 'application/json')

    def test_with_request_content_type_set(self):
        request = testing.DummyRequest()
        request.response_content_type = 'text/mishmash'
        renderer = self._callFUT('foo.jsonp')
        renderer({'a':1}, {'request':request})
        self.assertEqual(request.response_content_type, 'text/mishmash')

    def test_no_callback(self):
        renderer = self._callFUT(None)
        result = renderer({'a':1}, {})
        self.assertEqual(result, '{"a": 1}')

    def test_default_callback(self):
        renderer = self._callFUT(None)
        request = testing.DummyRequest()
        request.params['callback'] = 'callback1'
        result = renderer({'a':1}, {'request': request})
        self.assertEqual(result, 'callback1({"a": 1})')

    def test_override_callback_key(self):
        renderer = self._callFUT(None)
        request = testing.DummyRequest()
        request.params['jsonp_callback_key'] = 'jsonp'
        request.params['jsonp'] = 'callback2'
        result = renderer({'a':1}, {'request': request})
        self.assertEqual(result, 'callback2({"a": 1})')


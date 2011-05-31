import unittest

from repoze.bfg import testing
from testfixtures import Replacer
from webob.multidict import MultiDict

from opencore.views.api import get_template_api
from opencore.views.page import EditPageController, show_page


class TestViewPage(unittest.TestCase):

    def test_get(self):
        context = testing.DummyModel()
        context.title = 'A title'
        context.text = 'Some text'
        request = testing.DummyRequest()
        request.api = get_template_api(context, request)
        resp = show_page(context, request)
        self.assertTrue('api' in resp)
        self.assertEquals(resp['page'].title, 'A title')
        self.assertEquals(resp['page'].text, 'Some text')


class TestEditPageController(unittest.TestCase):

    def setUp(self):
        self.r = Replacer()
        self.r.replace('opencore.views.forms.get_current_request',
                       lambda: self.request)
        self.r.replace('opencore.views.forms.authenticated_userid',
                       lambda request: 'auth_user_id')

        testing.cleanUp()
        context = testing.DummyModel()
        context.title = 'title'
        context.text = 'content text'
        context.__name__ = 'my-page'
        self.context = context
        request = testing.DummyRequest()
        request.api = get_template_api(context, request)
        request.context = context
        self.request = request

    def tearDown(self):
        testing.cleanUp()
        self.r.restore()

    def _makeOne(self):
        return EditPageController(self.context, self.request)

    def test_get(self):
        controller = self._makeOne()
        info = controller()
        self.assertTrue('api' in info)
        self.assertTrue(info['form'].startswith('<form id="deform"'))

    def test_post(self):
        self.request.POST = MultiDict([
                ('title', u'New Title'),
                ('text', u'Lorem Ipsum'),
                ('save', u'save'),
                ])
        controller = self._makeOne()
        info = controller()
        self.assertEquals(self.context.title, "New Title")
        self.assertEquals(self.context.text, "Lorem Ipsum")

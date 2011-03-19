from datetime import datetime
import unittest

from zope.interface import implements
from zope.interface import Interface
from zope.interface import alsoProvides
from repoze.bfg.testing import cleanUp

from repoze.bfg import testing

from opencore.models.interfaces import IBlogEntry
from opencore.models.interfaces import IComment

from opencore.testing import DummyFile
from opencore.testing import DummySessions
from opencore.testing import registerLayoutProvider

class ShowCommentViewTests(unittest.TestCase):
    def setUp(self):
        cleanUp()
        registerLayoutProvider()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.commenting import show_comment_view
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        return show_comment_view(context, request)

    def test_it(self):
        context = testing.DummyModel(title='the title')

        request = testing.DummyRequest()
        def dummy_byline_info(context, request):
            return context
        from opencore.views.interfaces import IBylineInfo
        from opencore.models.interfaces import IBlogEntry
        alsoProvides(context, IBlogEntry)
        testing.registerAdapter(dummy_byline_info, (Interface, Interface),
                                IBylineInfo)
        renderer = testing.registerDummyRenderer('templates/show_comment.pt')
        response =self._callFUT(context, request)
        self.assertEqual(renderer.byline_info, context)


class RedirectCommentsTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.commenting import redirect_comments_view
        return redirect_comments_view(context, request)

    def test_redirect(self):
        context = testing.DummyModel()
        context.title = 'The comment'
        request = testing.DummyRequest()
        response = self._callFUT(context, request)
        self.assertEqual(response.location, 'http://example.com/')

    def test_redirect_with_status_message(self):
        context = testing.DummyModel()
        context.title = 'The comment'
        request = testing.DummyRequest({'status_message':'The status'})
        response = self._callFUT(context, request)
        self.assertEqual(response.location,
                         'http://example.com/?status_message=The status')

class DummyCommentsFolder(testing.DummyModel):

    @property
    def next_id(self):
        return u'99'


class DummyBlogEntry(testing.DummyModel):
    implements(IBlogEntry)

    title = "Dummy Blog Entry"
    __name__ = "DummyName"
    docid = 0

    def __init__(self, *arg, **kw):
        testing.DummyModel.__init__(self, *arg, **kw)
        self.comments = self["comments"] = DummyCommentsFolder()
        self["attachments"] = testing.DummyModel()
        self.arg = arg
        self.kw = kw

class DummyComment(testing.DummyModel):
    implements(IComment)

    text = "This is a test."
    title = "This is a comment."
    creator = u'a'

    def __init__(self, title, text, description, creator):
        testing.DummyModel.__init__(self,
            title=title,
            text=text,
            description=description,
            )

    def get_attachments(self):
        return self

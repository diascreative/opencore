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
from mock import Mock
from opencore.models.interfaces import IBlogEntry
from opencore.models.interfaces import IComment
from opencore.testing import DummyFile
from opencore.testing import DummySessions
from opencore.testing import registerLayoutProvider
from opencore.views.commenting import AddCommentController
from repoze.bfg.testing import cleanUp
from repoze.bfg import testing
from testfixtures import Replacer
from zope.interface import implements
from zope.interface import Interface
from zope.interface import alsoProvides

import unittest

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

class TestAddCommentController(unittest.TestCase):

    def setUp(self):
        self.context = testing.DummyModel(title='the title')
        self.request = testing.DummyRequest()
        self.controller = AddCommentController(self.context,self.request)

    def test_sanitize_html(self):
        self.request.method = 'POST'
        self.request.POST['comment.text']='some text'

        def dummy_safe_html(text):
            return u'filtered '+text

        dummy_handle_submit = Mock()
            
        with Replacer() as r:
            r.replace('opencore.views.commenting.safe_html',
                      dummy_safe_html)
            r.replace('opencore.views.commenting.AddCommentController.handle_submit',
                      dummy_handle_submit)

            self.controller()


        dummy_handle_submit.assert_called_with(dict(
            add_comment=u'filtered some text',
            attachments=[],
            ))

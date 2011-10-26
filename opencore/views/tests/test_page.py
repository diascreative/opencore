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
        testing.registerDummyRenderer('templates/page.pt')
        show_page(context, request)


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

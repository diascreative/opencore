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


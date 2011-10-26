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

        res = self._callFUT(context, request)
        self.assertNotEqual(res, None)

        self.assertEqual(res['id'], context.__name__)
        self.assertEqual(res['username'], context.__name__)
        self.assertEqual(res['firstname'], context.firstname)
        self.assertEqual(res['lastname'], context.lastname)
        self.assertEqual(res['email'], context.email)
        self.assertEqual(res['biography'], context.biography)
        self.assertEqual(res['joined'], context.created.strftime('%Y-%m-%dT%H:%M:%SZ'))
        self.assertEqual(res['websites'], context.websites)


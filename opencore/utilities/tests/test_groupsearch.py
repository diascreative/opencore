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

class TestLiveSearchGroup(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from opencore.utilities.groupsearch import GroupSearch
        return GroupSearch

    def _makeOne(self, context, request, interfaces, term):
        return self._getTargetClass()(context, request, interfaces, term)

    def _register(self, batch):
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        searchkw = {}
        def dummy_catalog_search(context):
            def resolver(x):
                return x
            def search(**kw):
                searchkw.update(kw)
                return len(batch), batch, resolver
            return search
        testing.registerAdapter(dummy_catalog_search, (Interface),
                                ICatalogSearch)
        return searchkw

    def test_makeCriteria(self):
        from repoze.bfg.testing import registerDummySecurityPolicy
        registerDummySecurityPolicy('fred', ['group:foo', 'group:bar'])
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from zope.interface import Interface
        thing = self._makeOne(context, request, [Interface], 'foo')
        criteria = thing._makeCriteria()
        self.assertEqual(criteria['texts'], 'foo')
        self.assertEqual(criteria['interfaces']['query'], [Interface])
        self.assertEqual(criteria['interfaces']['operator'], 'or')
        self.assertEqual(criteria['allowed']['query'],
                         ['system.Everyone', 'system.Authenticated',
                          'fred', 'group:foo', 'group:bar']
                         )
        self.assertEqual(criteria['allowed']['operator'], 'or')

    def test_get_batch(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from zope.interface import Interface
        self._register([1,2,3])
        thing = self._makeOne(context, request, [Interface], 'foo')
        batch = thing.get_batch()
        self.assertEqual(batch['entries'], [1,2,3])

    def test_call(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from zope.interface import Interface
        self._register([1,2,3])
        thing = self._makeOne(context, request, [Interface], 'foo')
        num, docids, resolver = thing()
        self.assertEqual(docids, [1,2,3])

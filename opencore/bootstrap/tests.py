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


# stdlib
import unittest

# Repoze
from repoze.bfg import testing
from repoze.bfg.configuration import Configurator
from repoze.bfg.threadlocal import get_current_registry

# opencore
from opencore.models.page import Page

class TestPopulate(unittest.TestCase):
    """
    XXX Integration test.
    """
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _registerComponents(self):
        # Install a bit of configuration that make_app() usually
        # does for us.
        reg = get_current_registry()
        config = Configurator(reg)
        config.setup_registry()
        config.load_zcml('opencore.includes:configure.zcml')

    def _callFUT(self, root, do_transaction_begin=True):
        from opencore.bootstrap.bootstrap import populate
        populate(root, do_transaction_begin=do_transaction_begin)

    def test_it(self):
        self._registerComponents()
        root = DummyDummy()
        connections = {}
        connections['main'] = DummyConnection(root, connections)
        root._p_jar = connections['main']

        self._callFUT(root, False)
        site = root['site']

        # Static pages
        expected_pages = ('funding', 'faq', 'about', 'contact')
        for expected in expected_pages:
            page = site[expected]
            self.assertTrue(isinstance(page, Page))

        ## TODO:
        #communities = site.get('communities')
        #self.failUnless(communities)
        #self.assertEqual(len(communities), 1)

    def test_external_catalog(self):
        self._registerComponents()
        root = DummyDummy()
        connections = {}
        connections['main'] = DummyConnection(root, connections)
        connections['catalog'] = DummyConnection(
            testing.DummyModel(), connections)
        root._p_jar = connections['main']

        self._callFUT(root, False)
        self.assertEquals(len(connections['catalog'].added), 1)

        catalog = connections['catalog'].root()['catalog']
        self.assertEquals(root['site'].catalog, catalog)

    def test_data_override(self):
        ## TODO
        pass

class DummySecurityWorkflow:
    initial_state_set = False

    def __init__(self, context):
        self.context = context

    def setInitialState(self):
        self.initial_state_set = True

class DummyConnection:
    def __init__(self, root, connections):
        self._root = root
        self.connections = connections
        self.added = []
    def get_connection(self, name):
        return self.connections[name]
    def root(self):
        return self._root
    def add(self, obj):
        self.added.append(obj)

class DummyDummy(dict):
    pass


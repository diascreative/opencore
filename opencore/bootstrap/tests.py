import unittest
from repoze.bfg import testing

from repoze.bfg.configuration import Configurator
from repoze.bfg.threadlocal import get_current_registry

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


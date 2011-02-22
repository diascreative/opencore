import unittest
from repoze.bfg import testing

class TestToolFactory(unittest.TestCase):
    def _makeOne(self):
        from opencore.models.tool import ToolFactory
        return ToolFactory()
    
    def test_add(self):
        factory = self._makeOne()
        context = testing.DummyModel()
        request = testing.DummyRequest()
        self.assertRaises(NotImplementedError, factory.add, context, request)

    def test_remove(self):
        factory = self._makeOne()
        context = testing.DummyModel()
        request = testing.DummyRequest()
        self.assertRaises(NotImplementedError, factory.remove, context, request)

    def test_is_present(self):
        factory = self._makeOne()
        context = testing.DummyModel()
        request = testing.DummyRequest()
        self.assertRaises(NotImplementedError, factory.is_present,
                          context, request)
        factory.name = 'thename'
        self.failIf(factory.is_present(context, request))
        context['thename'] = testing.DummyModel
        self.failUnless(factory.is_present(context, request))
        
    def test_is_current(self):
        from zope.interface import Interface
        from zope.interface import directlyProvides
        factory = self._makeOne()
        context = testing.DummyModel()
        request = testing.DummyRequest()
        self.assertRaises(NotImplementedError, factory.is_current,
                          context, request)
        class IDummy(Interface):
            pass
        factory.interfaces = (IDummy,)
        self.failIf(factory.is_current(context, request))
        directlyProvides(context, IDummy)
        request.context = context
        self.failUnless(factory.is_current(context, request))
        
    def test_tab_url(self):
        factory = self._makeOne()
        context = testing.DummyModel()
        request = testing.DummyRequest()
        self.assertRaises(NotImplementedError, factory.tab_url,
                          context, request)
        factory.name = 'thename'
        self.assertEqual(factory.tab_url(context, request),
                         'http://example.com/thename')
        
        

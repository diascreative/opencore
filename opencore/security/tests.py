import unittest
from repoze.bfg import testing

class TestACLPathCache(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.security.cache import ACLPathCache
        return ACLPathCache

    def _makeOne(self):
        return self._getTargetClass()()

    def _makeACE(self, allow=True, principal='phreddy', permission='testing'):
        from repoze.bfg.security import Allow
        from repoze.bfg.security import Deny
        action = allow and Allow or Deny
        return (action, principal, permission)

    def _makeModel(self, name=None, parent=None, principals=('phreddy',)):
        from repoze.bfg.testing import DummyModel
        model = DummyModel()
        if parent is not None:
            parent[name] = model
        if principals:
            model.__acl__ = [self._makeACE(principal=x) for x in principals]
        return model

    def test_class_conforms_to_IACLPathCache(self):
        from zope.interface.verify import verifyClass
        from opencore.security.interfaces import IACLPathCache
        verifyClass(IACLPathCache, self._getTargetClass())

    def test_instance_conforms_to_IACLPathCache(self):
        from zope.interface.verify import verifyObject
        from opencore.security.interfaces import IACLPathCache
        verifyObject(IACLPathCache, self._makeOne())

    def test_ctor(self):
        cache = self._makeOne()
        self.assertEqual(len(cache._index), 0)

    def test_clear_default(self):
        cache = self._makeOne()
        root = self._makeModel()
        cache.index(root)
        self.assertEqual(len(cache._index), 1)
        cache.clear()
        self.assertEqual(len(cache._index), 0)

    def test_clear_nondefault(self):
        cache = self._makeOne()
        root = self._makeModel()
        cache.index(root)
        child = self._makeModel(name='child', parent=root, principals=('bob',))
        cache.index(child)
        self.assertEqual(len(cache._index), 2)
        cache.clear(child)
        self.assertEqual(len(cache._index), 1)
        self.assertEqual(cache._index.keys()[0], ())

    def test_clear_intermediate(self):
        cache = self._makeOne()
        root = self._makeModel()
        cache.index(root)
        child = self._makeModel('child', root, principals=('bob',))
        cache.index(child)
        grand = self._makeModel('grand', child, principals=('alice',))
        cache.index(grand)
        self.assertEqual(len(cache._index), 3)
        cache.clear(child)
        self.assertEqual(len(cache._index), 1)
        self.assertEqual(cache._index.keys()[0], ())

    def test_index_no_acl(self):
        cache = self._makeOne()
        root = self._makeModel()
        cache.index(root)
        child = self._makeModel('child', root, principals=())
        cache.index(child)
        self.assertEqual(len(cache._index), 1)
        self.assertEqual(cache._index.keys()[0], ())

    def test_lookup_root_uncached_no_acl_no_permission(self):
        cache = self._makeOne()
        root = self._makeModel(principals=())

        aces = cache.lookup(root)
        self.assertEqual(len(aces), 0)
        self.assertEqual(len(cache._index), 0)

    def test_lookup_root_uncached_w_acl_no_permission(self):
        from repoze.bfg.security import Allow
        cache = self._makeOne()
        root = self._makeModel()

        aces = cache.lookup(root)
        self.assertEqual(len(aces), 1)
        self.assertEqual(aces[0], (Allow, 'phreddy', 'testing'))
        self.assertEqual(len(cache._index), 1)

    def test_lookup_root_cached_w_acl_no_permission(self):
        from repoze.bfg.security import Allow
        cache = self._makeOne()
        root = self._makeModel()
        cache.index(root)
        root.__acl__.append(self._makeACE(principal='bob'))  # uncached

        aces = cache.lookup(root)
        self.assertEqual(len(aces), 1, aces)
        self.assertEqual(aces[0], (Allow, 'phreddy', 'testing'))
        self.assertEqual(len(cache._index), 1)

    def test_lookup_nonroot(self):
        from repoze.bfg.security import Allow
        cache = self._makeOne()
        root = self._makeModel()
        child = self._makeModel('child', root, principals=('bob',))
        grand = self._makeModel('grand', child, principals=('alice',))

        aces = cache.lookup(grand)
        self.assertEqual(len(aces), 3)
        self.assertEqual(aces[0], (Allow, 'alice', 'testing'))
        self.assertEqual(aces[1], (Allow, 'bob', 'testing'))
        self.assertEqual(aces[2], (Allow, 'phreddy', 'testing'))
        self.assertEqual(len(cache._index), 3)

    def test_lookup_nonroot_w_permission(self):
        cache = self._makeOne()
        root = self._makeModel()
        child = self._makeModel('child', root, principals=('bob',))
        grand = self._makeModel('grand', child, principals=('alice',))

        aces = cache.lookup(grand, 'view')
        self.assertEqual(len(aces), 0)
        self.assertEqual(len(cache._index), 3)

    def test_lookup_nonroot_sparse(self):
        from repoze.bfg.security import Allow
        cache = self._makeOne()
        root = self._makeModel()
        child = self._makeModel('child', root, principals=('bob',))
        grand = self._makeModel('grand', child, principals=())

        aces = cache.lookup(grand)
        self.assertEqual(len(aces), 2)
        self.assertEqual(aces[0], (Allow, 'bob', 'testing'))
        self.assertEqual(aces[1], (Allow, 'phreddy', 'testing'))
        self.assertEqual(len(cache._index), 2)

    def test_lookup_nonroot_sparse_w_permission(self):
        cache = self._makeOne()
        root = self._makeModel()
        child = self._makeModel('child', root, principals=('bob',))
        grand = self._makeModel('grand', child, principals=())

        aces = cache.lookup(grand, 'view')
        self.assertEqual(len(aces), 0)
        self.assertEqual(len(cache._index), 2)

    def test_lookup_nonroot_sparse_w_permission_w_all(self):
        from repoze.bfg.security import Allow
        from opencore.security.policy import ALL
        cache = self._makeOne()
        root = self._makeModel()
        child = self._makeModel('child', root, principals=('bob',))
        grand = self._makeModel('grand', child, principals=())
        grand.__acl__ = [self._makeACE(True, 'alice', ALL)]

        aces = cache.lookup(grand, 'view')
        self.assertEqual(len(aces), 1)
        self.assertEqual(aces[0], (Allow, 'alice', ALL))
        self.assertEqual(len(cache._index), 3)

    def test_lookup_nonroot_sparse_w_allow_everyone(self):
        from repoze.bfg.security import Allow
        from repoze.bfg.security import Everyone
        cache = self._makeOne()
        root = self._makeModel()
        child = self._makeModel('child', root, principals=())
        child.__acl__ = [self._makeACE(True, Everyone)]
        grand = self._makeModel('grand', child, principals=('alice',))

        aces = cache.lookup(grand)
        self.assertEqual(len(aces), 2)
        self.assertEqual(aces[0], (Allow, 'alice', 'testing'))
        self.assertEqual(aces[1], (Allow, Everyone, 'testing'))
        self.assertEqual(len(cache._index), 2)

    def test_lookup_nonroot_sparse_w_deny_everyone(self):
        from repoze.bfg.security import Allow
        from repoze.bfg.security import Deny
        from repoze.bfg.security import Everyone
        cache = self._makeOne()
        root = self._makeModel()
        child = self._makeModel('child', root, principals=())
        child.__acl__ = [self._makeACE(True, 'bob'),
                         self._makeACE(False, Everyone)]
        grand = self._makeModel('grand', child, principals=('alice',))

        aces = cache.lookup(grand)
        self.assertEqual(len(aces), 3)
        self.assertEqual(aces[0], (Allow, 'alice', 'testing'))
        self.assertEqual(aces[1], (Allow, 'bob', 'testing'))
        self.assertEqual(aces[2], (Deny, Everyone, 'testing'))
        self.assertEqual(len(cache._index), 2)

class TestACLChecker(unittest.TestCase):
    def _getTargetClass(self):
        from opencore.security.policy import ACLChecker
        return ACLChecker

    def _makeOne(self, principals, permission):
        return self._getTargetClass()(principals, permission)

    def test_it(self):
        from repoze.bfg.security import Allow, Deny, Everyone
        from opencore.security.policy import ALL
        acl_one = ((Allow, 'a', 'view'), (Allow, 'b', 'view'))
        acl_two = ((Allow, 'c', 'view'), (Allow, 'd', 'view'),)
        acl_three = ((Allow, 'd', ALL), (Allow, 'e', 'view'),
                     (Deny, Everyone, ALL),)
        from BTrees.IFBTree import IFSet
        data = []
        data.append([(0, [acl_one],), IFSet([0])])
        data.append([(1, [acl_one, acl_two]), IFSet([1,2,3])])
        data.append([(2, [acl_one, acl_two, acl_three]), IFSet([4,5,6])])
        data.append([(3, [acl_one]), IFSet()])

        checker = self._makeOne(('a', Everyone), 'view')
        result = checker(data)
        self.assertEqual(list(result), [0, 1, 2, 3])

        checker = self._makeOne(('b', Everyone), 'view')
        result = checker(data)
        self.assertEqual(list(result), [0, 1, 2, 3])

        checker = self._makeOne(('c', Everyone), 'view')
        result = checker(data)
        self.assertEqual(list(result), [1, 2, 3])

        checker = self._makeOne(('d', Everyone), 'view')
        result = checker(data)
        self.assertEqual(list(result), [1, 2, 3, 4, 5, 6])

        checker = self._makeOne(('e', Everyone), 'view')
        result = checker(data)
        self.assertEqual(list(result), [4,5,6])

        checker = self._makeOne(('nobody', Everyone), 'view')
        result = checker(data)
        self.assertEqual(list(result), [])

class Test_acl_diff(unittest.TestCase):
    def _callFUT(self, ob, acl):
        from opencore.security.policy import acl_diff
        return acl_diff(ob, acl)

    def test_call_no_diff_has_acl(self):
        ob = DummyContent()
        ob.__acl__ = {}
        result = self._callFUT(ob, {})
        self.assertEqual(result, (None, None))

    def test_call_no_diff_has_no_acl(self):
        ob = DummyContent()
        result = self._callFUT(ob, {})
        self.assertEqual(result, (None, None))
        
    def test_call_diff_left(self):
        ob = DummyContent()
        ob.__acl__ = [('Allow', 'foo', ('bar',))]
        result = self._callFUT(ob, {})
        self.assertEqual(result, ('', 'Allow foo bar'))
        
    def test_call_diff_right(self):
        ob = DummyContent()
        ob.__acl__ = []
        result = self._callFUT(ob, [('Allow', 'foo', ('bar',))])
        self.assertEqual(result, ('Allow foo bar', ''))
        
    def test_call_diff_both(self):
        ob = DummyContent()
        ob.__acl__ = [('Allow', 'baz', ('buz'))]
        result = self._callFUT(ob, [('Allow', 'foo', ('bar',))])
        self.assertEqual(result, ('Allow foo bar', 'Allow baz buz'))

class Test_ace_repr(unittest.TestCase):
    def _callFUT(self, ace):
        from opencore.security.policy import ace_repr
        return ace_repr(ace)

    def test_with_permissions_iter(self):
        result = self._callFUT(('Allow', 'foo', ('buz',)))
        self.assertEqual(result, 'Allow foo buz')

    def test_with_permissions_not_iter(self):
        result = self._callFUT(('Allow', 'foo', 'buz'))
        self.assertEqual(result, 'Allow foo buz')

    def test_with_permissions_all(self):
        from opencore.security.policy import ALL
        result = self._callFUT(('Allow', 'foo', ALL))
        self.assertEqual(result, 'Allow foo ALL')

    def test_multiple_permissions(self):
        result = self._callFUT(('Allow', 'foo', ('edit', 'delete', 'view')))
        self.assertEqual(result, 'Allow foo delete, edit, view')


class DummyContent:
    pass


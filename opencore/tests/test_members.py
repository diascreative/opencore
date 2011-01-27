import unittest

class MembersFolderTests(unittest.TestCase):
    def _getTargetClass(self):
        from opencore.members import Members
        return Members

    def _makeOne(self, **kw):
        return self._getTargetClass()(**kw)

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from opencore.interfaces import IMembers
        verifyClass(IMembers, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from opencore.interfaces import IMembers
        verifyObject(IMembers, self._makeOne())


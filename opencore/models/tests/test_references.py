import unittest


class OrderingTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.models.references import Ordering
        return Ordering

    def _makeOne(self):
        return self._getTargetClass()()

    def test_class_conforms_to_IOrdering(self):
        from zope.interface.verify import verifyClass
        from opencore.models.interfaces import IOrdering
        verifyClass(IOrdering, self._getTargetClass())

    def test_instance_conforms_to_IOrdering(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IOrdering
        verifyObject(IOrdering, self._makeOne())

    def test_empty(self):
        ordering = self._makeOne()
        self.assertEqual(ordering.items(), [])

    def test_sync(self):
        ordering = self._makeOne()

        ordering.sync(['s1', 's2'])
        self.assertEqual(ordering.items(), [u's1', u's2'])

        ordering.sync(['s2'])
        self.assertEqual(ordering.items(), [u's2'])

        ordering.sync(['s3', 's2', 's4'])
        self.assertEqual(ordering.items(), [u's2', u's3', u's4'])

    def test_add_empty(self):
        ordering = self._makeOne()
        ordering.add(u's3')
        self.assertEqual(ordering.items(), [u's3'])

    def test_add_nonempty(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2'])
        ordering.add(u's3')
        self.assertEqual(ordering.items(), [u's1', u's2', u's3'])

    def test_add_duplicate(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2'])
        ordering.add(u's1')
        self.assertEqual(ordering.items(), [u's1', u's2'])

    def test_remove(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2', 's3', 's4'])
        ordering.remove(u's3')
        self.assertEqual(ordering.items(), [u's1', u's2', u's4'])

    def test_remove_nonesuch(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2'])
        ordering.remove(u's3')
        self.assertEqual(ordering.items(), [u's1', u's2'])

    def test_moveUp_middle(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2', 's3', 's4'])
        ordering.moveUp('s3')
        self.assertEqual(ordering.items(), [u's1', u's3', u's2', u's4'])

    def test_moveUp_top(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2', 's3', 's4'])
        ordering.moveUp('s1')
        self.assertEqual(ordering.items(), [u's2', u's3', u's4', u's1'])

    def test_moveDown_middle(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2', 's3', 's4'])
        ordering.moveDown ('s1')
        self.assertEqual(ordering.items(), [u's2', u's1', u's3', u's4'])

    def test_moveDown_end(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2', 's3', 's4'])
        ordering.moveDown ('s4')
        self.assertEqual(ordering.items(), [u's4', u's1', u's2', u's3'])

    def test_previous_next(self):
        ordering = self._makeOne()
        ordering.sync(['s1', 's2', 's3', 's4'])
        self.assertEqual(ordering.previous_name(u's2'), u's1')
        self.assertEqual(ordering.previous_name(u's1'), None)
        self.assertEqual(ordering.next_name(u's3'), u's4')
        self.assertEqual(ordering.next_name(u's4'), None)


class ReferenceSectionTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.models.references import ReferenceSection
        return ReferenceSection

    def _makeOne(self, title=u'', description=u'', creator=u'admin'):
        return self._getTargetClass()(title, description, creator)

    def test_class_conforms_to_IReferenceSection(self):
        from zope.interface.verify import verifyClass
        from opencore.models.interfaces import IReferenceSection
        verifyClass(IReferenceSection, self._getTargetClass())

    def test_instance_conforms_to_IReferenceSection(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IReferenceSection
        verifyObject(IReferenceSection, self._makeOne())

    def test_instance_has_valid_construction(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IOrdering
        instance = self._makeOne()
        self.assertEqual(instance.title, u'')
        self.assertEqual(instance.description, u'')
        self.assertEqual(instance.creator, u'admin')
        self.assertEqual(instance.modified_by, u'admin')
        verifyObject(IOrdering, instance.ordering)


class ReferenceManualTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.models.references import ReferenceManual
        return ReferenceManual

    def _makeOne(self, title=u'', description=u'', creator=u'admin'):
        return self._getTargetClass()(title, description, creator)

    def test_class_conforms_to_IReferenceSection(self):
        from zope.interface.verify import verifyClass
        from opencore.models.interfaces import IReferenceSection
        verifyClass(IReferenceSection, self._getTargetClass())

    def test_instance_conforms_to_IReferenceSection(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IReferenceSection
        verifyObject(IReferenceSection, self._makeOne())

    def test_class_conforms_to_IReferenceManual(self):
        from zope.interface.verify import verifyClass
        from opencore.models.interfaces import IReferenceManual
        verifyClass(IReferenceManual, self._getTargetClass())

    def test_instance_conforms_to_IReferenceManual(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IReferenceManual
        verifyObject(IReferenceManual, self._makeOne())

    def test_instance_has_valid_construction(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IOrdering
        instance = self._makeOne()
        self.assertEqual(instance.title, u'')
        self.assertEqual(instance.description, u'')
        self.assertEqual(instance.creator, u'admin')
        self.assertEqual(instance.modified_by, u'admin')
        verifyObject(IOrdering, instance.ordering)

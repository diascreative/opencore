
import unittest

class PageTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.models.page import Page
        return Page

    def _makeOne(self, title=u'title', text=u'text', description=u'text',
            creator=u'admin'):
        return self._getTargetClass()(title, text, description, creator)

    def test_class_conforms_to_IPage(self):
        from zope.interface.verify import verifyClass
        from opencore.models.interfaces import IPage
        verifyClass(IPage, self._getTargetClass())

    def test_instance_conforms_to_IPage(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IPage
        verifyObject(IPage, self._makeOne())

    def test_instance_has_valid_construction(self):
        instance = self._makeOne()
        self.assertEqual(instance.title, u'title')
        self.assertEqual(instance.text, u'text')
        self.assertEqual(instance.description, u'text')
        self.assertEqual(instance.creator, u'admin')
        self.assertEqual(instance.modified_by, u'admin')

        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IAttachmentsFolder
        verifyObject(IAttachmentsFolder, instance['attachments'])

    def test_instance_construct_with_none(self):
        instance = self._makeOne(text=u'<div>x</div>')
        self.assertEqual(instance.text, u'<div>x</div>')


class DummyContent:
    pass

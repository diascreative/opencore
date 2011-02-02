import unittest

from repoze.bfg import testing

class AttachmentsFolderTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.content.models.attachments import AttachmentsFolder
        return AttachmentsFolder

    def _makeOne(self):
        return self._getTargetClass()()

    def test_class_conforms_to_IAttachmentsFolder(self):
        from zope.interface.verify import verifyClass
        from opencore.interfaces import IAttachmentsFolder
        verifyClass(IAttachmentsFolder, self._getTargetClass())

    def test_instance_conforms_to_IAttachmentsFolder(self):
        from zope.interface.verify import verifyObject
        from opencore.interfaces import IAttachmentsFolder
        verifyObject(IAttachmentsFolder, self._makeOne())

    def test_next_id_nomembers(self):
        attachments = self._makeOne()
        self.assertEqual(attachments.next_id, '1')
        
    def test_next_id_wthmembers(self):
        attachments = self._makeOne()
        attachments['1'] = testing.DummyModel()
        self.assertEqual(attachments.next_id, '2')

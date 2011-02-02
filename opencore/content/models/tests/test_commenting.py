import unittest

from repoze.bfg import testing

class CommentsFolderTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.content.models.commenting import CommentsFolder
        return CommentsFolder

    def _makeOne(self):
        return self._getTargetClass()()

    def test_class_conforms_to_ICommentsFolder(self):
        from zope.interface.verify import verifyClass
        from opencore.interfaces import ICommentsFolder
        verifyClass(ICommentsFolder, self._getTargetClass())

    def test_instance_conforms_to_ICommentsFolder(self):
        from zope.interface.verify import verifyObject
        from opencore.interfaces import ICommentsFolder
        verifyObject(ICommentsFolder, self._makeOne())

    def test_next_id_nomembers(self):
        attachments = self._makeOne()
        self.assertEqual(attachments.next_id, '001')

    def test_next_id_wthmembers(self):
        attachments = self._makeOne()
        attachments['001'] = testing.DummyModel()
        self.assertEqual(attachments.next_id, '002')

    def test_next_id_lots_of_members(self):
        attachments = self._makeOne()
        for i in xrange(1,200):
            next_id = attachments.next_id
            self.assertEqual(next_id, u"%03d" % i)
            attachments[next_id] = testing.DummyModel()


class CommentTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.content.models.commenting import Comment
        return Comment

    def _makeOne(self, title=u'title', text=u'text', description=u'',
                 creator=u'admin',
                 ):
        return self._getTargetClass()(
            title, text, description, creator)

    def test_class_conforms_to_IComment(self):
        from zope.interface.verify import verifyClass
        from opencore.interfaces import IComment
        verifyClass(IComment, self._getTargetClass())

    def test_instance_conforms_to_IComment(self):
        from zope.interface.verify import verifyObject
        from opencore.interfaces import IComment
        verifyObject(IComment, self._makeOne())

    def test_instance_has_valid_construction(self):
        instance = self._makeOne()
        self.assertEqual(instance.title, u'title')
        self.assertEqual(instance.text, u'text')
        self.assertEqual(instance.creator, u'admin')
        self.assertEqual(instance.modified_by, u'admin')

    def test_instance_construct_with_none(self):
        instance = self._makeOne(text=None)
        self.assertEqual(instance.text, u'')

    def test_instance_construct_with_no_description(self):
        instance = self._makeOne(description=None)
        self.assertEqual(instance.description, u'')

    def test_get_attachments(self):
        instance = self._makeOne(text=None)
        self.assertEqual(instance.get_attachments(), instance)

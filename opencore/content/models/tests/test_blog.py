import unittest
from repoze.bfg import testing
from zope.testing.cleanup import cleanUp

class BlogTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.content.models.blog import Blog
        return Blog

    def _makeOne(self):
        return self._getTargetClass()()

    def test_class_conforms_to_IBlog(self):
        from zope.interface.verify import verifyClass
        from opencore.content.interfaces import IBlog
        verifyClass(IBlog, self._getTargetClass())

    def test_instance_conforms_to_IBlog(self):
        from zope.interface.verify import verifyObject
        from opencore.content.interfaces import IBlog
        verifyObject(IBlog, self._makeOne())

class BlogEntryTests(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.content.models.blog import BlogEntry
        return BlogEntry

    def _makeOne(self, title=u'title', text=u'text', description=u'text',
                 creator=u'admin',
                 ):
        return self._getTargetClass()(
            title, text, description, creator)

    def test_class_conforms_to_IBlogEntry(self):
        from zope.interface.verify import verifyClass
        from opencore.content.interfaces import IBlogEntry
        verifyClass(IBlogEntry, self._getTargetClass())

    def test_instance_conforms_to_IBlogEntry(self):
        from zope.interface.verify import verifyObject
        from opencore.content.interfaces import IBlogEntry
        verifyObject(IBlogEntry, self._makeOne())

    def test_instance_has_valid_construction(self):
        instance = self._makeOne()
        self.assertEqual(instance.title, u'title')
        self.assertEqual(instance.text, u'text')
        self.assertEqual(instance.description, u'text')
        self.assertEqual(instance.creator, u'admin')
        self.assertEqual(instance.modified_by, u'admin')
        self.failUnless('comments' in instance)

        from zope.interface.verify import verifyObject
        from opencore.interfaces import ICommentsFolder
        verifyObject(ICommentsFolder, instance['comments'])

    def test_get_attachments(self):
        instance = self._makeOne()
        self.assertEqual(instance.get_attachments(), instance['attachments'])

class TestBlogToolFactory(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _makeOne(self):
        from opencore.content.models.blog import blog_tool_factory
        return blog_tool_factory

    def test_it(self):
        from repoze.lemonade.interfaces import IContentFactory
        testing.registerAdapter(lambda *arg, **kw: DummyContent, (None,),
                                IContentFactory)
        context = testing.DummyModel()
        request = testing.DummyRequest
        factory = self._makeOne()
        factory.add(context, request)
        self.failUnless(context['blog'])
        self.failUnless(factory.is_present(context, request))
        factory.remove(context, request)
        self.failIf(factory.is_present(context, request))


class DummyContent:
    pass

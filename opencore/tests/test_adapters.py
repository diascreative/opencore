import unittest

from repoze.bfg import testing
from zope.interface import Interface
from opencore import testing as ocoretesting

class TestDeprecatedCatalogSearch(unittest.TestCase):

    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from opencore.adapters import CatalogSearch
        return CatalogSearch

    def _makeOne(self, context, request):
        global __warningregistry__
        import warnings
        old_filters = warnings.filters[:]
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        try:
            adapter = self._getTargetClass()(context, request)
        finally:
            warnings.filters[:] = old_filters 
        assert __warningregistry__
        del __warningregistry__
        return adapter

    def test_it(self):
        context = testing.DummyModel()
        context.catalog = ocoretesting.DummyCatalog({})
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        num, docids, resolver = adapter()
        self.assertEqual(num, 0)
        self.assertEqual(list(docids), [])

    def test_unfound_model(self):
        from repoze.bfg.interfaces import ILogger
        class DummyLogger:
            def warn(self, msg):
                self.msg = msg
        logger = DummyLogger()
        testing.registerUtility(logger, ILogger, 'repoze.bfg.debug')
        a = testing.DummyModel()
        b = testing.DummyModel()
        testing.registerModels({'/a':a})
        context = testing.DummyModel()
        context.catalog = ocoretesting.DummyCatalog({1:'/a', 2:'/b'})
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        num, docids, resolver = adapter()
        self.assertEqual(num, 2)
        self.assertEqual(list(docids), [1, 2])
        results = filter(None, map(resolver, docids))
        self.assertEqual(results, [a])
        self.assertEqual(logger.msg, 'Model missing: /b')
      
    def test_unfound_docid(self):
        context = testing.DummyModel()
        context.catalog = ocoretesting.DummyCatalog({})
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        num, docids, resolver = adapter()
        self.assertEqual(resolver(123), None)


class TestCatalogSearch(unittest.TestCase):

    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from opencore.adapters import CatalogSearch
        return CatalogSearch

    def _makeOne(self, context):
        adapter = self._getTargetClass()(context)
        return adapter

    def test_it(self):
        context = testing.DummyModel()
        context.catalog = ocoretesting.DummyCatalog({})
        adapter = self._makeOne(context)
        num, docids, resolver = adapter()
        self.assertEqual(num, 0)
        self.assertEqual(list(docids), [])

    def test_unfound_model(self):
        from repoze.bfg.interfaces import ILogger
        class DummyLogger:
            def warn(self, msg):
                self.msg = msg
        logger = DummyLogger()
        testing.registerUtility(logger, ILogger, 'repoze.bfg.debug')
        a = testing.DummyModel()
        b = testing.DummyModel()
        testing.registerModels({'/a':a})
        context = testing.DummyModel()
        context.catalog = ocoretesting.DummyCatalog({1:'/a', 2:'/b'})
        adapter = self._makeOne(context)
        num, docids, resolver = adapter()
        self.assertEqual(num, 2)
        self.assertEqual(list(docids), [1, 2])
        results = filter(None, map(resolver, docids))
        self.assertEqual(results, [a])
        self.assertEqual(logger.msg, 'Model missing: /b')

    def test_unfound_docid(self):
        context = testing.DummyModel()
        context.catalog = ocoretesting.DummyCatalog({})
        adapter = self._makeOne(context)
        num, docids, resolver = adapter()
        self.assertEqual(resolver(123), None)


class TestGridEntryInfo(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.adapters import GridEntryInfo
        return GridEntryInfo

    def _makeOne(self, context, request):
        return self._getTargetClass()(context, request)

    def test_class_conforms_to_IGridEntryInfo(self):
        from zope.interface.verify import verifyClass
        from opencore.interfaces import IGridEntryInfo
        verifyClass(IGridEntryInfo, self._getTargetClass())

    # instance wont conform due to properties

    def test_title(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        context.title = 'title'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.title, 'title')

    def test_url(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.url, 'http://example.com/')

    def test_comment_url(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        commentfolder = testing.DummyModel()
        grandparent = testing.DummyModel()
        grandparent['commentfolder'] = commentfolder
        commentfolder['0123'] = context
        from zope.interface import directlyProvides
        from opencore.interfaces import IComment
        directlyProvides(context, IComment)
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.url, 'http://example.com/#comment-0123')

    def test_type(self):
        from zope.interface import Interface
        from zope.interface import taggedValue
        from zope.interface import directlyProvides
        from repoze.lemonade.testing import registerContentFactory
        request = testing.DummyRequest()
        context = testing.DummyModel()
        class Dummy:
            pass
        class IDummy(Interface):
            taggedValue('name', 'yo')
        registerContentFactory(Dummy, IDummy)
        directlyProvides(context, IDummy)
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.type, 'yo')

    def test_modified(self):
        import datetime
        request = testing.DummyRequest()
        context = testing.DummyModel()
        now = datetime.datetime.now()
        context.modified = now
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.modified,now.strftime("%m/%d/%Y"))

    def test_created(self):
        import datetime
        request = testing.DummyRequest()
        context = testing.DummyModel()
        now = datetime.datetime.now()
        context.created = now
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.created,now.strftime("%m/%d/%Y"))

    def test_creator_title(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        creator = testing.DummyModel(title='Dummy creator')
        context['profiles'] = profiles = testing.DummyModel()
        profiles['creator'] = creator
        context.creator = 'creator'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.creator_title,
                         'Dummy creator')

    def test_creator_without_title(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        creator = testing.DummyModel()
        context['profiles'] = profiles = testing.DummyModel()
        profiles['creator'] = creator
        context.creator = 'creator'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.creator_title,
                         'no profile title')

    def test_creator_url(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        creator = testing.DummyModel(title='Dummy creator')
        context['profiles'] = profiles = testing.DummyModel()
        profiles['creator'] = creator
        context.creator = 'creator'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.creator_url,
                         'http://example.com/profiles/creator/')

    def test_modified_by_title_falls_back_to_creator(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        profile = testing.DummyModel(title='Test User')
        context['profiles'] = profiles = testing.DummyModel()
        profiles['testuser'] = profile
        context.creator = 'testuser'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.modified_by_title, 'Test User')

    def test_modified_by_title(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        profile = testing.DummyModel(title='Test User')
        context['profiles'] = profiles = testing.DummyModel()
        profiles['testuser'] = profile
        context.modified_by = 'testuser'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.modified_by_title, 'Test User')

    def test_modified_by_without_title(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        profile = testing.DummyModel()
        context['profiles'] = profiles = testing.DummyModel()
        profiles['testuser'] = profile
        context.modified_by = 'testuser'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.modified_by_title, 'no profile title')

    def test_modified_by_without_profile(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        profile = testing.DummyModel()
        context['profiles'] = profiles = testing.DummyModel()
        context.modified_by = 'testuser'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.modified_by_title, 'no profile title')

    def test_modified_by_url(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        from opencore.interfaces import ISite
        from zope.interface import directlyProvides
        directlyProvides(context, ISite)
        profile = testing.DummyModel(title='Test User')
        context['profiles'] = profiles = testing.DummyModel()
        profiles['testuser'] = profile
        context.modified_by = 'testuser'
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.modified_by_url,
                         'http://example.com/profiles/testuser/')


class TestTagQuery(unittest.TestCase):

    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from opencore.adapters import TagQuery
        return TagQuery

    def _makeOne(self, context, request):
        manager = self._getTargetClass()(context, request)
        manager.iface = DummyInterface
        return manager

    def test_tags_with_counts(self):
        from zope.interface import directlyProvides
        from opencore import testing as ocoretesting
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.catalog = ocoretesting.DummyCatalog()

        def dummy_getTagObjects(*args, **kw):
            self.assertEqual(kw['items'], (123,))
            return [testing.DummyModel(name='tag1', user='nyc1'),
                    testing.DummyModel(name='tag1', user='admin'),
                    testing.DummyModel(name='tag2', user='nyc1'),
                   ]
        dummy_tags = testing.DummyModel()
        dummy_tags.getTagObjects = dummy_getTagObjects
        context.tags = dummy_tags
        directlyProvides(context, DummyInterface)
        adapter = self._makeOne(context, request)
        adapter._docid = 123
        adapter.username = u'admin'

        alltaginfo = adapter.tagswithcounts

        self.assertEqual(len(alltaginfo), 2, alltaginfo)
        self.assertEqual(alltaginfo[0]['count'], 2)
        self.assertEqual(alltaginfo[0]['tag'], u'tag1')
        self.assertEqual(alltaginfo[0]['snippet'], '')
        self.assertEqual(alltaginfo[1]['count'], 1)
        self.assertEqual(alltaginfo[1]['tag'], u'tag2')
        self.assertEqual(alltaginfo[1]['snippet'], 'nondeleteable')

    def test_tagusers(self):
        context = testing.DummyModel()
        tags = context.tags = testing.DummyModel()
        def _getTags(*args, **kw):
            self.assertEqual(kw['users'], ('dummy',))
            self.assertEqual(kw['items'], (1,))
            return ['1', '2']
        tags.getTags = _getTags
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        adapter._docid = 1
        adapter.username = u'dummy'
        self.assertEqual(adapter.tagusers, '1 2')

    def test_docid(self):
        from opencore import testing as ocoretesting
        request = testing.DummyRequest()
        context = testing.DummyModel()
        context.catalog = ocoretesting.DummyCatalog()
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.docid, None)

    def test_tags_with_prefix(self):
        request = testing.DummyRequest()
        context = testing.DummyModel()
        tags = testing.DummyModel()
        tags.getTagsWithPrefix = lambda x: x
        context.tags = tags
        adapter = self._makeOne(context, request)
        generator = adapter.tags_with_prefix('1')
        self.assertEqual(list(generator), ['1'])


class TestCommunityInfo(unittest.TestCase):

    def _getTargetClass(self):
        from opencore.adapters import CommunityInfo
        return CommunityInfo

    def _makeOne(self, context, request):
        return self._getTargetClass()(context, request)

    def _makeCommunity(self, **kw):
        community = testing.DummyModel(title='title', description='description')
        return community

    def test_class_conforms_to_ICommunityInfo(self):
        from zope.interface.verify import verifyClass
        from opencore.interfaces import ICommunityInfo
        verifyClass(ICommunityInfo, self._getTargetClass())

    # instance wont conform due to properties

    def test_number_of_members(self):
        context = self._makeCommunity()
        request = testing.DummyRequest()
        context.number_of_members = 3
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.number_of_members, 3)

    def test_tabs_requestcontext_iscommunity(self):
        from opencore.interfaces import ICommunity
        from opencore.interfaces import IToolFactory
        from repoze.lemonade.testing import registerListItem
        from zope.interface import directlyProvides
        tool_factory = DummyToolFactory()
        registerListItem(IToolFactory, tool_factory, 'one', title='One')
        context = self._makeCommunity()
        directlyProvides(context, ICommunity)
        request = testing.DummyRequest()
        request.context = context
        adapter = self._makeOne(context, request)
        tabs = adapter.tabs
        self.assertEqual(len(tabs), 2)
        self.assertEqual(tabs[0],
                         {'url': 'http://example.com/view.html',
                          'css_class': 'curr', 'name': 'OVERVIEW'}
                         )
        self.assertEqual(tabs[1],
                         {'url': 'http://example.com/tab',
                          'css_class': '', 'name': 'ONE'}
                         )

    def test_tabs_requestcontext_is_not_community(self):
        from opencore.interfaces import IToolFactory
        from repoze.lemonade.testing import registerListItem
        tool_factory = DummyToolFactory()
        registerListItem(IToolFactory, tool_factory, 'one', title='One')
        context = self._makeCommunity()
        request = testing.DummyRequest()
        request.context = context
        adapter = self._makeOne(context, request)
        tabs = adapter.tabs
        self.assertEqual(len(tabs), 2)
        self.assertEqual(tabs[0],
                         {'url': 'http://example.com/view.html',
                          'css_class': '', 'name': 'OVERVIEW'}
                         )
        self.assertEqual(tabs[1],
                         {'url': 'http://example.com/tab',
                          'css_class': 'curr', 'name': 'ONE'}
                         )

    def test_description(self):
        context = self._makeCommunity()
        context.description = 'description'
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.description, 'description')

    def test_title(self):
        context = self._makeCommunity()
        context.title = 'title'
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.title, 'title')

    def test_name(self):
        context = self._makeCommunity()
        context.__name__ = 'name'
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.name, 'name')

    def test_last_activity_date(self):
        context = self._makeCommunity()
        import datetime
        now = datetime.datetime.now()
        context.content_modified = now
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.last_activity_date, now.strftime("%m/%d/%Y"))

    def test_url(self):
        context = self._makeCommunity()
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        self.assertEqual(adapter.url, 'http://example.com/')

    def test_community_tags_no_tags_tool(self):
        context = self._makeCommunity()
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)
        self.assertEqual(len(adapter.community_tags), 0)

    def test_community_tags_wo_tags_tool_less_than_five(self):
        context = self._makeCommunity()
        context.__name__ = 'dummy'
        tool = context.tags = DummyTags([('foo', 3), ('bar', 6)])
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)

        tags = adapter.community_tags

        self.assertEqual(len(tags), 2)
        self.assertEqual(tags[0], {'tag': 'bar', 'count': 6})
        self.assertEqual(tags[1], {'tag': 'foo', 'count': 3})
        self.assertEqual(tool._called_with, 'dummy')

    def test_community_tags_wo_tags_tool_more_than_five(self):
        context = self._makeCommunity()
        context.tags = DummyTags([('foo', 3),
                                  ('bar', 6),
                                  ('baz', 14),
                                  ('qux', 1),
                                  ('quxxy', 4),
                                  ('spam', 2),
                                 ])
        request = testing.DummyRequest()
        adapter = self._makeOne(context, request)

        tags = adapter.community_tags

        self.assertEqual(len(tags), 5)
        self.assertEqual(tags[0], {'tag': 'baz', 'count': 14})
        self.assertEqual(tags[1], {'tag': 'bar', 'count': 6})
        self.assertEqual(tags[2], {'tag': 'quxxy', 'count': 4})
        self.assertEqual(tags[3], {'tag': 'foo', 'count': 3})
        self.assertEqual(tags[4], {'tag': 'spam', 'count': 2})

    def test_is_member_direct(self):
        context = self._makeCommunity()
        context.member_names = ['dummy', 'foo']
        request = testing.DummyRequest()
        testing.registerDummySecurityPolicy('dummy')
        adapter = self._makeOne(context, request)

        self.assertEqual(adapter.member, True)

    def test_is_member_via_group(self):
        context = self._makeCommunity()
        context.member_names = ['a_group', 'foo']
        request = testing.DummyRequest()
        testing.registerDummySecurityPolicy('dummy', ['a_group'])
        adapter = self._makeOne(context, request)

        self.assertEqual(adapter.member, True)

    def test_is_not_member(self):
        context = self._makeCommunity()
        context.member_names = ['foo', 'bar']
        request = testing.DummyRequest()
        testing.registerDummySecurityPolicy('dummy')
        adapter = self._makeOne(context, request)

        self.assertEqual(adapter.member, False)

    def test_is_moderator(self):
        context = self._makeCommunity()
        context.moderator_names = ['dummy', 'foo']
        request = testing.DummyRequest()
        testing.registerDummySecurityPolicy('dummy')
        adapter = self._makeOne(context, request)

        self.assertEqual(adapter.moderator, True)

    def test_is_not_moderator(self):
        context = self._makeCommunity()
        context.moderator_names = ['foo', 'bar']
        request = testing.DummyRequest()
        testing.registerDummySecurityPolicy('dummy')
        adapter = self._makeOne(context, request)

        self.assertEqual(adapter.moderator, False)

class DummyTags:
    _called_with = None

    def __init__(self, tags=()):
        self._tags = tags

    def getFrequency(self, tags=None, community=None):
        assert tags is None
        self._called_with = community
        return self._tags


class DummyToolFactory:
    def is_present(self, context, request):
        return True

    def tab_url(self, context, request):
        return 'http://example.com/tab'

    def is_current(self, context, request):
        return True


class DummyInterface(Interface):
    pass


class DummyFieldIndex:
    def __init__(self, data={}):
        self._fwd_index = data

import unittest

from repoze.bfg import testing

from opencore import testing as oitesting

class RedirectCommunityViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.community import redirect_community_view
        return redirect_community_view(context, request)

    def test_it(self):
        from opencore.models.interfaces import ICommunity
        from zope.interface import directlyProvides
        context = testing.DummyModel()
        directlyProvides(context, ICommunity)
        context.default_tool = 'murg'
        request = testing.DummyRequest()
        response = self._callFUT(context, request)
        self.assertEqual(response.location, 'http://example.com/murg')

    def test_it_notool(self):
        from opencore.models.interfaces import ICommunity
        from zope.interface import directlyProvides
        context = testing.DummyModel()
        directlyProvides(context, ICommunity)
        request = testing.DummyRequest()
        response = self._callFUT(context, request)
        self.assertEqual(response.location, 'http://example.com/view.html')

class ShowCommunityViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _register(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ITagQuery
        from opencore.models.interfaces import ICommunityInfo
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.interfaces import IGridEntryInfo
        from opencore.models.adapters import CatalogSearch
        testing.registerAdapter(DummyTagQuery, (Interface, Interface),
                                ITagQuery)
        testing.registerAdapter(DummyGridEntryAdapter, (Interface, Interface),
                                IGridEntryInfo)
        testing.registerAdapter(DummyAdapter, (Interface, Interface),
                                ICommunityInfo)
        testing.registerAdapter(CatalogSearch, (Interface), ICatalogSearch)

    def _callFUT(self, context, request):
        from opencore.views.community import show_community_view
        return show_community_view(context, request)

    def _makeCommunity(self):
        from zope.interface import directlyProvides
        from opencore.models.interfaces import ICommunity
        community = testing.DummyModel(title='thetitle')
        community.member_names = community.moderator_names = set()
        directlyProvides(community, ICommunity)
        foo = testing.DummyModel(__name__='foo')
        catalog = oitesting.DummyCatalog({1:'/foo'})
        testing.registerModels({'/foo':foo})
        community.catalog = catalog
        return community

    def test_not_a_member(self):
        from repoze.bfg.url import model_url
        self._register()
        context = self._makeCommunity()
        request = testing.DummyRequest()
        info = self._callFUT(context, request)
        self.assertEqual(info['actions'],
                         [('Edit', 'edit.html'),
                          ('Join', 'join.html'),
                          ('Delete', 'delete.html'),
                         ])
        self.assertEqual(info['feed_url'],
                         model_url(context, request, "atom.xml"))
        self.assertEqual(len(info['recent_items']), 1)
        self.assertEqual(info['recent_items'][0].context.__name__, 'foo')

    def test_already_member(self):
        self._register()
        context = self._makeCommunity()
        context.member_names = set(('userid',))
        request = testing.DummyRequest()
        testing.registerDummySecurityPolicy('userid')
        info = self._callFUT(context, request)
        self.assertEqual(info['actions'],
                         [('Edit', 'edit.html'),
                          ('Delete', 'delete.html'),
                         ])

class CommunityRecentItemsAjaxViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _register(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.interfaces import IGridEntryInfo
        from opencore.models.adapters import CatalogSearch
        testing.registerAdapter(DummyGridEntryAdapter, (Interface, Interface),
                                IGridEntryInfo)
        testing.registerAdapter(CatalogSearch, (Interface), ICatalogSearch)

    def _callFUT(self, context, request):
        from opencore.views.community import community_recent_items_ajax_view
        return community_recent_items_ajax_view(context, request)

    def _makeCommunity(self):
        from zope.interface import directlyProvides
        from opencore.models.interfaces import ICommunity
        community = testing.DummyModel(title='thetitle')
        directlyProvides(community, ICommunity)
        foo = testing.DummyModel(__name__='foo')
        catalog = oitesting.DummyCatalog({1:'/foo'})
        testing.registerModels({'/foo':foo})
        community.catalog = catalog
        return community

    def test_simple(self):
        self._register()
        context = self._makeCommunity()
        request = testing.DummyRequest()
        info = self._callFUT(context, request)
        self.assertEqual(len(info['items']), 1)
        self.assertEqual(info['items'][0].context.__name__, 'foo')

class CommunityMembersAjaxViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _register(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.interfaces import IGridEntryInfo
        from opencore.models.adapters import CatalogSearch
        testing.registerAdapter(DummyGridEntryAdapter, (Interface, Interface),
                                IGridEntryInfo)
        testing.registerAdapter(CatalogSearch, (Interface), ICatalogSearch)

    def _callFUT(self, context, request):
        from opencore.views.community import community_members_ajax_view
        return community_members_ajax_view(context, request)

    def _makeCommunity(self):
        from zope.interface import directlyProvides
        from opencore.models.interfaces import ICommunity
        community = testing.DummyModel(title='thetitle')
        catalog = oitesting.DummyCatalog({1: '/profiles/phred',
                                            2: '/profiles/bharney',
                                            3: '/profiles/wylma',
                                           })
        phred = testing.DummyModel(__name__='phred')
        bharney = testing.DummyModel(__name__='bharney')
        wylma = testing.DummyModel(__name__='wylma')
        testing.registerModels({'/profiles/phred':phred,
                                '/profiles/bharney':bharney,
                                '/profiles/wylma':wylma,
                               })
        community.catalog = catalog
        community.member_names = set(['phred', 'bharney', 'wylma'])
        community.moderator_names = set(['bharney'])
        directlyProvides(community, ICommunity)
        return community

    def test_simple(self):
        self._register()
        context = self._makeCommunity()
        request = testing.DummyRequest()
        info = self._callFUT(context, request)
        self.assertEqual(len(info['items']), 3)
        self.assertEqual(info['items'][0].context.__name__, 'bharney')
        self.assertEqual(info['items'][1].context.__name__, 'phred')
        self.assertEqual(info['items'][2].context.__name__, 'wylma')

class RelatedCommunitiesAjaxViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.community import related_communities_ajax_view
        return related_communities_ajax_view(context, request)

    def _register(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.interfaces import IGridEntryInfo
        from opencore.models.adapters import CatalogSearch
        testing.registerAdapter(DummyGridEntryAdapter, (Interface, Interface),
                                IGridEntryInfo)
        testing.registerAdapter(CatalogSearch, (Interface), ICatalogSearch)

    def _makeCommunity(self, results=None):
        from zope.interface import directlyProvides
        from opencore.models.interfaces import ICommunity
        if results is None:
            results = [{}]
        community = testing.DummyModel(title='Interests Align')
        catalog = oitesting.DummyCatalog(*results)
        community.catalog = catalog
        directlyProvides(community, ICommunity)
        return community

    def test_it_no_matches(self):
        from opencore.models.interfaces import ICommunity
        self._register()
        context = self._makeCommunity()
        request = testing.DummyRequest()
        info = self._callFUT(context, request)
        self.assertEqual(info['items'], [])
        self.assertEqual(context.catalog.queries,
                         [{'interfaces': [ICommunity],
                           'limit': 5,
                           'reverse': True,
                           'sort_index': 'modified_date',
                           'texts': 'interests OR align',
                           'allowed': {'query': [], 'operator': 'or'}
                          }])

class JoinCommunityViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.community import join_community_view
        return join_community_view(context, request)

    def test_show_form(self):
        c = oitesting.DummyCommunity()
        site = c.__parent__.__parent__
        profiles = site["profiles"] = testing.DummyModel()
        profiles["user"] = oitesting.DummyProfile()
        renderer = testing.registerDummyRenderer("templates/join_community.pt")
        testing.registerDummySecurityPolicy("user")
        request = testing.DummyRequest()
        testing.registerDummyRenderer(
            'opencore.views:templates/formfields.pt')
        self._callFUT(c, request)
        self.assertEqual(renderer.profile, profiles["user"])
        self.assertEqual(renderer.community, c)
        self.assertEqual(
            renderer.post_url,
            "http://example.com/communities/community/join.html"
        )

    def test_submit_form(self):
        from repoze.sendmail.interfaces import IMailDelivery
        testing.registerDummyRenderer("templates/join_community.pt")

        c = oitesting.DummyCommunity()
        c.moderator_names = set(["moderator1", "moderator2"])
        site = c.__parent__.__parent__
        profiles = site["profiles"] = testing.DummyModel()
        profiles["user"] = oitesting.DummyProfile()
        profiles["moderator1"] = oitesting.DummyProfile()
        profiles["moderator2"] = oitesting.DummyProfile()

        mailer = oitesting.DummyMailer()
        testing.registerUtility(mailer, IMailDelivery)

        testing.registerDummySecurityPolicy("user")
        request = testing.DummyRequest({
            "form.submitted": "1",
            "message": "Message text.",
        })
        testing.registerDummyRenderer(
            'opencore.views:templates/email_join_community.pt')
        response = self._callFUT(c, request)

        self.assertEqual(response.location,
                         "http://example.com/communities/community/"
                         "?status_message=Your+request+has+been+sent+"
                         "to+the+moderators.")
        self.assertEqual(len(mailer), 1)
        msg = mailer.pop()
        self.assertEqual(msg.mto, ["moderator1@x.org",
                                   "moderator2@x.org"])
        self.assertEqual(msg.mfrom, "user@x.org")

class DeleteCommunityViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.community import delete_community_view
        return delete_community_view(context, request)

    def _register(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ICommunityInfo
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.adapters import CatalogSearch
        testing.registerAdapter(DummyAdapter, (Interface, Interface),
                                ICommunityInfo)
        testing.registerAdapter(CatalogSearch, (Interface), ICatalogSearch)

    def test_not_confirmed(self):
        from opencore.testing import registerLayoutProvider
        registerLayoutProvider()

        request = testing.DummyRequest()
        context = testing.DummyModel(title='oldtitle')
        context.__name__  = 'thename'
        context.catalog = oitesting.DummyCatalog({})
        context.users = oitesting.DummyUsers({})
        testing.registerDummyRenderer('templates/delete_resource.pt')
        self._register()
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '200 OK')

    def test_confirmed(self):
        request = testing.DummyRequest({'confirm':'1'})
        context = testing.DummyModel(title='oldtitle')
        parent = DummyParent()
        parent['thename'] = context
        parent.catalog = oitesting.DummyCatalog({})
        parent.users = oitesting.DummyUsers({})
        testing.registerDummyRenderer('templates/delete_resource.pt')
        self._register()
        testing.registerDummySecurityPolicy('userid')
        response = self._callFUT(context, request)
        self.assertEqual(parent.deleted, 'thename')
        self.assertEqual(response.location, 'http://example.com/')

class DummyToolFactory:
    def __init__(self, present=False):
        self.present = present

    def add(self, context, request):
        self.added = True

    def remove(self, context, request):
        self.removed = True

    def is_present(self, context, request):
        return self.present

class DummyParent(testing.DummyModel):
    def __delitem__(self, name):
        self.deleted = name

class DummyAdapter:
    def __init__(self, context, request):
        self.context = context
        self.request = request

class DummyTagQuery(DummyAdapter):
    tagswithcounts = []
    docid = 'ABCDEF01'

class DummyGridEntryAdapter(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

class DummyForm:
    def __init__(self):
        self.widgets = {}
        self.allfields = []

    def validate(self, request, render, succeed):
        pass

    def __call__(self):
        pass

    def set_widget(self, name, field):
        self.widgets[name] = field
        self.allfields.append(field)

class DummySchema:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class DummyCommunity:
    def __init__(self, title, description, text, creator):
        self.title = title
        self.description = description
        self.text = text
        self.creator = self.modified_by = creator
        self.members_group_name = 'members'
        self.moderators_group_name = 'moderators'

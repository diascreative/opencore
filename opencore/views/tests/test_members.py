import unittest

from repoze.bfg import testing
from repoze.bfg.testing import registerAdapter
from repoze.lemonade.testing import registerContentFactory
from repoze.sendmail.interfaces import IMailDelivery
from opencore import testing as oitesting
from opencore.models.interfaces import (
    ICatalogSearch,
    ICommunity,
    IInvitation,
    IProfile,
    IProfiles,
    )
from opencore.utilities.interfaces import IRandomId
from opencore.views.api import get_template_api
from opencore.views.forms import BaseController
from opencore.views.members import (
    MembersBaseController,
    AcceptInvitationController,
    InviteNewUsersController,
    JoinNewUsersController,
    ManageMembersController,
    )
from webob.multidict import MultiDict
from zope.interface import (
    Interface,
    directlyProvides,
    )

class Base(unittest.TestCase):
    
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _registerMailer(self):
        mailer = oitesting.DummyMailer()
        testing.registerUtility(mailer, IMailDelivery)
        return mailer

class MemberBaseContollerTests(unittest.TestCase):
    
    def setUp(self):
        self.context = testing.DummyModel()
        self.request = testing.DummyRequest()
        self.request.api = get_template_api(self.context, self.request)
        self.controller = MembersBaseController(self.context,self.request)

    def test_community(self):
        self.assertEqual(self.controller.community,None)

    def test_actions(self):
        self.assertEqual(
            self.controller.actions,
            [('Manage Members', 'manage.html'),
             ('Add', 'invite_new.html')]
            )

    def test_profiles(self):
        self.assertEqual(self.controller.profiles,None)

    def test_system_name(self):
        self.assertEqual(self.controller.system_name,'OpenCore')

    
class ShowMembersViewTests(Base):

    def _callFUT(self, context, request):
        from opencore.views.members import show_members_view
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        return show_members_view(context, request)

    def test_show_members(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        context = testing.DummyModel()
        context.member_names = ['a']
        context.moderator_names = ['b']
        profiles = testing.DummyModel()
        profiles['a'] = oitesting.DummyProfile()
        profiles['b'] = oitesting.DummyProfile()
        context['profiles'] = profiles
        d = {1:profiles['a'], 2:profiles['b']}
        searchkw = {}
        def resolver(docid):
            return d.get(docid)
        def dummy_catalog_search(context):
            def search(**kw):
                searchkw.update(kw)
                return 2, [1,2], resolver
            return search
        testing.registerAdapter(dummy_catalog_search, (Interface),
                                ICatalogSearch)
        from opencore.models.interfaces import ICommunity
        from zope.interface import directlyProvides
        directlyProvides(context, ICommunity)
        request = testing.DummyRequest(params={'hide_pictures':True})
        renderer = testing.registerDummyRenderer('templates/show_members.pt')
        self._callFUT(context, request)
        actions = [('Manage Members', 'manage.html'),
                   ('Add', 'invite_new.html')]
        self.assertEqual(renderer.actions, actions)
        self.assertEqual(len(renderer.members), 2)
        self.assertEqual(len(renderer.moderators), 1)
        self.assertEqual(renderer.hide_pictures, True)
        self.assertEqual(len(renderer.submenu), 2)
        self.assertEqual(renderer.submenu[0]['make_link'], True)
        self.assertEqual(renderer.submenu[1]['make_link'], False)
        self.assertEqual(searchkw['sort_index'], 'lastfirst')

class CommunityBase(Base):
    
    def setUp(self):
        Base.setUp(self)
        self.request = testing.DummyRequest()
        self.context = self._makeContext()
        self.request.api = get_template_api(self.context, self.request)
        self.mailer = self._registerMailer()
        registerCatalogSearch()
        def nonrandom(size=6):
            return 'A' * size
        testing.registerUtility(nonrandom, IRandomId)
        registerContentFactory(DummyProfiles, IProfiles)
        registerContentFactory(DummyInvitation, IInvitation)
        self.context['profiles'] = self.profiles = DummyProfiles()
        
class InviteNewUsersControllerBase(CommunityBase):
    
    def _makeOne(self):
        return InviteNewUsersController(self.context, self.request)

class AddExistingUserTests(InviteNewUsersControllerBase):

    def _makeContext(self):
        context = testing.DummyModel()
        directlyProvides(context, ICommunity)
        context.users = oitesting.DummyUsers()
        context.title = 'thetitle'
        context.description = 'description'
        context.members_group_name = 'members'
        context['profiles'] = testing.DummyModel()
        admin = testing.DummyModel()
        admin.email = 'admin@example.com'
        context['profiles']['admin'] = admin

        return context
    
    def test_get_with_userid(self):
        self.request.params['user_id']='admin'
        self.profiles['admin'] = oitesting.DummyProfile()
        
        controller = self._makeOne()
        
        response = controller()
        self.assertEqual(self.context.users.added_groups,
                         [('admin','members')])
        self.assertEqual(self.mailer[0].mto[0], 'admin@x.org')
        self.failUnless(
            response.location.startswith('http://example.com/manage.html'))

    def test_handle_submit_badprofile(self):
        controller = self._makeOne()
        
        self.request.POST = MultiDict([
                ('__start__', u'users:sequence'),
                ('a_user[]', u'nyc99'),
                ('__end__', u'users:sequence'),
                ('send', u'send')
                ])
        response = controller()

        self.assertEqual(self.context.users.added_groups, [])

        # The KarlUserWidget doesn't currently show error messages.
        # Since I don't think this code path can actually get executed
        # in real use, I'm punting for now...
        # self.failUnless('This is not a valid profile.' in response['form'])

    def test_handle_submit_success(self):
        self.profiles['admin'] = oitesting.DummyProfile()
        
        controller = self._makeOne()

        self.request.POST = MultiDict([
                ('__start__', u'users:sequence'),
                ('a_user', u'admin'),
                ('__end__', u'users:sequence'),
                ('send', u'send')
                ])
        
        response = controller()
        self.assertEqual(self.context.users.added_groups,
                         [('admin','members')])
        self.assertEqual(self.mailer[0].mto[0], 'admin@x.org')
        self.failUnless(
            response.location.startswith('http://example.com/manage.html'))

class AcceptInvitationControllerTests(CommunityBase):

    def _makeContext(self):
        context = testing.DummyModel(sessions=DummySessions())
        directlyProvides(context, ICommunity)
        context.title = 'The Community'
        context.communities_name = 'test_commmunity'
        context.users = oitesting.DummyUsers()
        return context

    def _makeOne(self):
        return AcceptInvitationController(self.context, self.request)

    def test_get(self):
        controller = self._makeOne()
        info = controller()
        self.failUnless('api' in info)
        self.assertTrue(info['form'].startswith('<form id="deform"'))
   
    def test_handle_submit_password_mismatch(self):
        controller = self._makeOne()
        self.request.POST = MultiDict([
                ('__start__', u'account:mapping'),
                ('__start__', u'password:mapping'),
                ('value', u'1'),
                ('confirm', u'2'),
                ('__end__', u'password:mapping'),
                ('__end__', u'account:mapping'),
                ('join up', u'join up')
                ])
        info = controller()
        self.failUnless('Password did not match confirm' in info['form'])
        
    def test_handle_submit_username_exists(self):
        self.profiles['a'] = oitesting.DummyProfile()
        
        controller = self._makeOne()
        self.request.POST = MultiDict([
                ('__start__', u'account:mapping'),
                ('username', u'a'),
                ('__end__', u'account:mapping'),
                ('join up', u'join up')
                ])
        info = controller()
        self.failUnless('This username is already taken' in info['form'])
        
    def test_handle_submit_bad_username(self):
        controller = self._makeOne()
        self.request.POST = MultiDict([
                ('__start__', u'account:mapping'),
                ('username', u'a !!'),
                ('__end__', u'account:mapping'),
                ('join up', u'join up')
                ])
        info = controller()
        self.failUnless(
            'only letters, numbers, and dashes' in info['form']
            )
        
    def test_handle_submit_missing_tou(self):
        controller = self._makeOne()
        self.request.POST = MultiDict([
                ('join up', u'join up')
                ])
        info = controller()
        self.failUnless(
            'You must agree to the terms of use' in info['form']
            )
        
    def test_handle_submit_success(self):
        registerContentFactory(oitesting.DummyProfile, IProfile)
        class DummyWhoPlugin(object):
            def remember(self, environ, identity):
                self.identity = identity
                return []
        plugin = DummyWhoPlugin()
        whoplugins = {'auth_tkt':plugin}
        self.request.environ['repoze.who.plugins'] = whoplugins
        community = self.context
        community.members_group_name = 'community:members'
        context = testing.DummyModel()
        community['invite'] = context
        community.title = 'Community'
        community.description = 'Community'
        community.sessions = DummySessions()
        context.email = 'a@example.com'
        self.context = context
        
        controller = self._makeOne()
        self.request.POST = MultiDict([
                ('__start__', u'account:mapping'),
                ('username', u'username'),
                ('__start__', u'password:mapping'),
                ('value', u'safe'),
                ('confirm', u'safe'),
                ('__end__', u'password:mapping'),
                ('__end__', u'account:mapping'),
                ('__start__', u'details:mapping'),
                ('first_name', u'Joe'),
                ('last_name', u'Marks'),
                ('country', u'ZW'),
                ('__start__', u'date_of_birth:mapping'),
                ('year', u''),
                ('month', u''),
                ('day', u''),
                ('__end__', u'date_of_birth:mapping'),
                ('gender', u''),
                ('__end__', u'details:mapping'),
                ('__start__', u'terms:mapping'),
                ('terms_of_use', u'true'),
                ('__end__', u'terms:mapping'),
                ('join up', u'join up')
                ])
        
        response = controller()

        self.assertEqual(response.location,
                         'http://example.com/?status_message=Welcome%21')
        self.assertEqual(community.users.added,
                         ('username', 'username', 'safe', ['community:members']))
        self.assertEqual(plugin.identity, {'repoze.who.userid':'username'})
        profiles = community['profiles']
        self.failUnless('username' in profiles)
        self.assertEqual(profiles['username'].security_state, 'active')
        self.failIf('invite' in community)
        self.assertEqual(len(self.mailer), 1)

class InviteNewUsersTests(InviteNewUsersControllerBase):

    redirect_url = '/redirect-location'

    def _makeContext(self):
        community = testing.DummyModel()
        community.member_names = set(['a'])
        community.moderator_names = set(['b', 'c'])
        users = oitesting.DummyUsers(community)
        community.users = users
        directlyProvides(community, ICommunity)
        community.moderators_group_name = 'group:community:moderators'
        community.members_group_name = 'group:community:members'
        community.title = 'community'
        community.description = 'description'
        return community

    def test_get(self):
        controller = self._makeOne()
        info = controller()
        self.failUnless('api' in info)
        self.failUnless('actions' in info)
        self.assertTrue(info['form'].startswith('<form id="deform"'))
        self.assertFalse(self.redirect_url in info['form'])

    def test_get_with_redirect(self):
        self.request = testing.DummyRequest(
                params={'return_to': self.redirect_url})
        self.request.api = get_template_api(self.context, self.request)
        controller = self._makeOne()
        info = controller()
        self.assertTrue(self.redirect_url in info['form'])
   
    def test_handle_submit_no_users_or_emails(self):
        
        controller = self._makeOne()

        self.request.POST = MultiDict([
                ('text', u'some text'),
                ('send', u'send')
                ])
        response = controller()
        
        self.failUnless('you must supply' in response['form'])

    def test_handle_submit_new_to_system(self):
        
        controller = self._makeOne()

        self.request.POST = MultiDict([
                ('email_addresses', u'yo@plope.com'),
                ('text', u'some text'),
                ('return_to', u'http://example.com/some-redirection'),
                ('send', u'send')
                ])
        response = controller()
        self.assertTrue(u"top.location = 'http://example.com/some-redirection'" in response.body)
        invitation = self.context['A'*6]
        self.assertEqual(invitation.email, 'yo@plope.com')
        self.assertEqual(1, len(self.mailer))
        self.assertEqual(self.mailer[0].mto, [u"yo@plope.com",])

    def test_handle_submit_already_in_system(self):
        self.profiles['d'] = profile = oitesting.DummyProfile()
        registerCatalogSearch(results={'email=d@x.org': [profile,]})
        
        controller = self._makeOne()
        
        self.request.POST = MultiDict([
                ('email_addresses', u'd@x.org'),
                ('text', u'some text'),
                ('send', u'send')
                ])
        response = controller()
        
        self.assertEqual(response.location,
          'http://example.com/manage.html?status_message=One+existing+user+added+to+community.++'
                         )
        self.failIf('A'*6 in self.context)
        self.assertEqual(self.context.users.added_groups,
                         [('d', 'group:community:members')])

    def test_handle_submit_inactive_user(self):
        self.profiles['e'] = profile = oitesting.DummyProfile(security_state='inactive')
        registerCatalogSearch(results={'email=e@x.org': [profile,]})
        
        controller = self._makeOne()
        
        self.request.POST  = MultiDict([
                ('email_addresses', u'e@x.org'),
                ('text', u'some text'),
                ('send', u'send')
                ])
        response = controller()

        self.failUnless('previously been deactivated' in response['form'])
        
        self.failIf('A'*6 in self.context)
        self.assertEqual(self.context.users.added_groups,[])

    def test_handle_submit_already_in_community(self):
        self.profiles['a'] = profile = oitesting.DummyProfile()
        registerCatalogSearch(results={'email=a@x.org': [profile,]})
        
        controller = self._makeOne()
        
        self.request.POST  = MultiDict([
                ('email_addresses', u'a@x.org'),
                ('text', u'some text'),
                ('send', u'send')
                ])
        response = controller()
        
        self.assertEqual(response.location,
          'http://example.com/manage.html?status_message=One+user+already+member.'
                         )
        self.failIf('A'*6 in self.context)
        self.assertEqual(self.context.users.added_groups, [])


class ManageMembersControllerTests(Base):

    def _makeOne(self, context, request):
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        return ManageMembersController(context, request)

    def _makeContext(self):
        community = testing.DummyModel()
        community.member_names = set(['a'])
        community.moderator_names = set(['b', 'c'])
        site = testing.DummyModel()
        site['communities'] = testing.DummyModel()
        site['communities']['community'] = community
        profiles = testing.DummyModel()
        profiles['a'] = oitesting.DummyProfile()
        profiles['b'] = oitesting.DummyProfile()
        profiles['c'] = oitesting.DummyProfile()
        invitation = testing.DummyModel(email='foo@example.com',
                                        message='message')
        directlyProvides(invitation, IInvitation)
        community['invitation'] = invitation
        site['profiles'] = profiles
        self.site = site
        users = oitesting.DummyUsers(community)
        site.users = users
        directlyProvides(community, ICommunity)
        community.moderators_group_name = 'moderators'
        community.members_group_name = 'members'
        return community

    def test_form_defaults(self):
        context = self._makeContext()
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)

        defaults = controller.form_defaults()
        members = defaults['members']
        self.assertEqual(len(members), 4)

        self.assertEqual(members[0]['member'], True)
        self.assertEqual(members[0]['name'], 'c')
        self.assertEqual(members[0]['moderator'], True)

        self.assertEqual(members[1]['member'], True)
        self.assertEqual(members[1]['name'], 'b')
        self.assertEqual(members[1]['moderator'], True)

        self.assertEqual(members[2]['member'], True)
        self.assertEqual(members[2]['name'], 'a')
        self.assertEqual(members[2]['moderator'], False)

        self.assertEqual(members[3]['member'], False)
        self.assertEqual(members[3]['name'], 'invitation')
        self.assertEqual(members[3]['moderator'], False)

    def test_call(self):
        context = self._makeContext()
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer(
            'opencore.views:templates/members_manage.pt')
        controller = self._makeOne(context, request)
        result = controller()
        self.failUnless(hasattr(renderer, 'api'))
        self.failUnless(hasattr(renderer, 'actions'))
        self.failUnless(hasattr(renderer,'page_title'))

  
    def test_handle_submit_remove_sole_moderator(self):
        from opencore.views.validation import ValidationError
        context = self._makeContext()
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
        request.POST = {'remove_b' : 'True', 'remove_c' : 'True'}
        request.method = 'POST'
        self.assertRaises(ValidationError, controller)
    
    def test_handle_submit_remove_member(self):
        renderer = testing.registerDummyRenderer(
            'opencore.views:templates/members_manage.pt')
        context = self._makeContext()
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
        request.POST = {'remove_a' : 'True'}
        request.method = 'POST'
        mailer = self._registerMailer()
        response = controller()
        site = context.__parent__.__parent__
        users = site.users
        self.assertEqual(users.removed_groups, [(u'a', 'members')])
        self.assertEqual(context.member_names, set([]))
        self.assertEqual(len(mailer), 0)
        self.assertEqual(response.location,
                         'http://example.com/communities/community/'
                         'manage.html?status_message='
                         'Membership+information+changed%3A+'
                         'Removed+member+title')

    def test_handle_submit_remove_invitation(self):
        context = self._makeContext()
        request = testing.DummyRequest()
        context.member_names = set([])
        controller = self._makeOne(context, request)
        request.POST = {'remove_invitation' : 'True'}
        request.method = 'POST'
        mailer = self._registerMailer()
        response = controller()
        site = context.__parent__.__parent__
        users = site.users
        self.assertEqual(len(mailer), 0)
        self.failIf('invitation' in context)
        self.assertEqual(response.location,
                         'http://example.com/communities/community/'
                         'manage.html?status_message='
                         'Membership+information+changed%3A+'
                         'Removed+invitation+foo%40example.com')

    def test_handle_submit_resend(self):
        testing.registerDummyRenderer(
            'opencore.views:templates/members_manage.pt')
        context = self._makeContext()
        context.title = 'community'
        context.description = 'description'
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
        request.POST = {'resend_invitation' : 'True'}
        request.method = 'POST'
        mailer = self._registerMailer()
        response = controller()
        self.assertEqual(len(mailer), 1)
        self.assertEqual(response.location,
                         'http://example.com/communities/community/'
                         'manage.html?status_message='
                         'Membership+information+changed%3A+'
                         'Resent+invitation+to+foo%40example.com')

    def test_handle_submit_add_moderator(self):
        context = self._makeContext()
        context.title = 'community'
        context.description = 'description'
        self.site['profiles']['a'].title = 'Flash'
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
       
        request.method = 'POST'
        request.POST = {'moderator_a' : u'True'}
        mailer = self._registerMailer()
        response = controller()
        self.assertEqual(len(mailer), 0)
        self.assertEqual(response.location,
                         'http://example.com/communities/community/'
                         'manage.html?status_message='
                         'Membership+information+changed%3A+'
                         'Flash+is+now+a+moderator')

class TestJoinNewUsersController(CommunityBase):

    def setUp(self):
        Base.setUp(self)
        self.request = testing.DummyRequest()
        self.context = self._makeContext()
        self.request.api = get_template_api(self.context, self.request)
        self.mailer = self._registerMailer()
        def nonrandom(size=6):
            return 'A' * size
        testing.registerUtility(nonrandom, IRandomId)
        registerContentFactory(DummyInvitation, IInvitation)
        self.context['profiles'] = self.profiles = DummyProfiles()

    def _makeContext(self):
        context = testing.DummyModel()
        directlyProvides(context, ICommunity)
        context.users = oitesting.DummyUsers()
        context.title = 'thetitle'
        context.description = 'description'
        context.members_group_name = 'members'
        context['profiles'] = testing.DummyModel()
        admin = testing.DummyModel()
        admin.email = 'admin@example.com'
        context['profiles']['admin'] = admin
        return context
        
    def _makeOne(self):
        return JoinNewUsersController(self.context,self.request)

    def test_subclass(self):
        # so we can assume all the base controller bits work ;-)
        self.assertTrue(isinstance(self._makeOne(),BaseController))
    
    def test_get(self):
        controller = self._makeOne()
        
        info = controller()
        
        self.assertTrue('api' in info)
        self.assertTrue(info['form'].startswith('<form id="deform"'))
    

    def test_post_inactive(self):
        profile = oitesting.DummyProfile()
        profile.security_state='inactive'
        search = oitesting.DummySearch(profile)
        
        registerAdapter(lambda context:search, (Interface,), ICatalogSearch)
        
        self.request.POST = MultiDict([
                ('email_address',u'aDmIn@x.com'),
                ('signup', u'signup')
                ])

        controller = self._makeOne()
        info = controller()

        # check search spec
        self.assertEqual(search.spec,
                ((),{'interfaces': [IProfile], 'email': u'admin@x.com'}))
        
        self.failUnless(
            'This address belongs to a user which has ' in info['form']
            )
    
    def test_post_already_a_member(self):
        profile = oitesting.DummyProfile()
        search = oitesting.DummySearch(profile)
        
        registerAdapter(lambda context:search, (Interface,), ICatalogSearch)
        
        self.request.POST = MultiDict([
                ('email_address',u'aDmIn@x.com'),
                ('signup', u'signup')
                ])

        controller = self._makeOne()
        info = controller()

        # check search spec
        self.assertEqual(search.spec,
                ((),{'interfaces': [IProfile], 'email': u'admin@x.com'}))
        
        self.failUnless(
            'This email address is already registered.' in info['form']
            )

    def test_post_success(self):
        search = oitesting.DummySearch()
        
        registerAdapter(lambda context:search, (Interface,), ICatalogSearch)
        
        self.request.POST = MultiDict([
                ('email_address',u'aDmIn@x.com'),
                ('signup', u'signup')
                ])

        controller = self._makeOne()
        response = controller()

        self.assertEqual(
            response.location,
            '/?status_message=You have been sent a signup email.'
            )

        self.assertEqual(self.context['AAAAAA'].email,
                         'aDmIn@x.com')
        self.assertEqual(self.context['AAAAAA'].message,
                         "We look forward to you joining.")

class TestJqueryMemberSearchView(Base):

    def _callFUT(self, context, request):
        from opencore.views.members import jquery_member_search_view
        return jquery_member_search_view(context, request)

    def test_it(self):
        from zope.interface import Interface
        from zope.interface import directlyProvides
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.interfaces import ICommunity
        context = testing.DummyModel()
        directlyProvides(context, ICommunity)
        context.member_names = set('a',)
        context.moderator_names = set()
        request = testing.DummyRequest(params={'tag':'a'})
        profiles = testing.DummyModel()
        profile_1 = oitesting.DummyProfile(__name__='a',
                                             security_state='active')
        profile_2 = oitesting.DummyProfile(__name__='b',
                                             security_state='active')
        profile_3 = oitesting.DummyProfile(__name__='c',
                                             security_state='active')
        profile_4 = oitesting.DummyProfile(__name__='d',
                                             security_state='inactive')
        def resolver(docid):
            d = {1:profile_1, 2:profile_2, 3:profile_3, 4:profile_4}
            return d.get(docid)
        def dummy_catalog_search(context):
            def search(**kw):
                return 3, [1,2,3], resolver
            return search
        testing.registerAdapter(dummy_catalog_search, (Interface),
                                ICatalogSearch)
        response = self._callFUT(context, request)

        self.assertEqual(
            response.body,
            '[{"value": "title", "key": "b"}, '
            '{"value": "title", "key": "c"}]')

class DummyMembers(testing.DummyModel):
    def __init__(self):
        testing.DummyModel.__init__(self)
        self.__parent__ = oitesting.DummyCommunity()
        self.__name__ = 'members'

class DummyInvitation:
    def __init__(self, email, message):
        self.email = email
        self.message = message

class DummyContent:
    def __init__(self, **kw):
        for key,value in kw.items():
            setattr(self, key, value)

class DummyProfiles(testing.DummyModel):
    def __init__(self):
        testing.DummyModel.__init__(self)

def dummy_search(results):
    class DummySearchAdapter:
        def __init__(self, context, request=None):
            self.context = context
            self.request = request

        def __call__(self, **kw):
            search = []
            for k,v in kw.items():
                key = '%s=%s' % (k,v)
                if key in results:
                    search.extend(results[key])

            return len(search), search, lambda x: x

    return DummySearchAdapter

class DummyInvitationBoilerPlate(object):
    terms_and_conditions = "Do this.  Don't do that."
    privacy_statement = "We won't sell you out."

    def __init__(self, context, request):
        pass

def registerCatalogSearch(results={}):
    registerAdapter(dummy_search(results), (Interface,), ICatalogSearch)

class DummySessions(dict):
    def get(self, name, default=None):
        if name not in self:
            self[name] = {}
        return self[name]

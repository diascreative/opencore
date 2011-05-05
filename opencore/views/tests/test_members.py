import unittest

from repoze.bfg import testing
from repoze.lemonade.testing import registerContentFactory
from repoze.sendmail.interfaces import IMailDelivery
from opencore import testing as oitesting
from opencore.models.interfaces import (
    ICommunity,
    IInvitation,
    IProfiles,
    )
from opencore.utilities.interfaces import IRandomId
from opencore.views.api import get_template_api
from opencore.views.members import (
    InviteNewUsersController,
    ManageMembersController,
    )
from webob.multidict import MultiDict
from zope.interface import directlyProvides

class Base(unittest.TestCase):
    
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _registerMailer(self):
        mailer = oitesting.DummyMailer()
        testing.registerUtility(mailer, IMailDelivery)
        return mailer

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

class AddExistingUserTests(Base):

    def _makeOne(self, context, request):
        from opencore.views.members import InviteNewUsersController
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        return InviteNewUsersController(context, request)

    def _getContext(self):
        context = testing.DummyModel()
        from opencore.models.interfaces import ICommunity
        from zope.interface import directlyProvides
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
    
    def test__call__(self):
        context = self._getContext()
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
        info = controller()
        actions = [('Manage Members', 'manage.html'),
                   ('Add', 'invite_new.html')]
        
        self.assertEqual(info['actions'], actions)
       

    def test___call__with_userid_get(self):
        from repoze.sendmail.interfaces import IMailDelivery
        request = testing.DummyRequest({"user_id": "admin"})
        context = self._getContext()
        mailer = oitesting.DummyMailer()
        testing.registerUtility(mailer, IMailDelivery)
        controller = self._makeOne(context, request)
        testing.registerDummyRenderer(
            'opencore.views:templates/email_add_existing.pt')
        response = controller()
        self.assertEqual(context.users.added_groups, [('admin','members')])
        self.assertEqual(mailer[0].mto[0], 'admin@example.com')
        self.failUnless(
            response.location.startswith('http://example.com/manage.html'))

    def test_handle_submit_badprofile(self):
        from opencore.views.validation import ValidationError
        request = testing.DummyRequest()
        context = self._getContext()
        controller = self._makeOne(context, request)
        request.method = 'POST'
        request.POST = {'users':('admin', 'nyc99'), 'text':'some text'}
        self.assertRaises(ValidationError, controller)

    def test_handle_submit_success(self):
        from repoze.sendmail.interfaces import IMailDelivery
        request = testing.DummyRequest()
        context = self._getContext()
        mailer = oitesting.DummyMailer()
        testing.registerUtility(mailer, IMailDelivery)
        controller = self._makeOne(context, request)
        request.method = "POST"
        request.POST = {'users': (u'admin',), 'text':'some_text'}
        testing.registerDummyRenderer(
            'opencore.views:templates/email_add_existing.pt')
        response = controller()
        self.assertEqual(context.users.added_groups, [('admin','members')])
        self.assertEqual(mailer[0].mto[0], 'admin@example.com')
        self.failUnless(
            response.location.startswith('http://example.com/manage.html'))

class AcceptInvitationControllerTests(Base):

    def _makeContext(self):
        from opencore.models.interfaces import ICommunity
        from zope.interface import directlyProvides
        context = testing.DummyModel(sessions=DummySessions())
        directlyProvides(context, ICommunity)
        context.title = 'The Community'
        return context

    def _makeRequest(self):
        request = testing.DummyRequest()
        request.environ['repoze.browserid'] = '1'
        return request

    def _makeOne(self, context, request):
        from opencore.views.members import AcceptInvitationController
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        context.communities_name = 'test_commmunity'
        return AcceptInvitationController(context, request)

    def test__call__(self):
        context = self._makeContext()
        request = self._makeRequest()
        renderer = testing.registerDummyRenderer(
            'templates/accept_invitation.pt')
      
        controller = self._makeOne(context, request)
        info = controller()
      
        self.failUnless('page_title' in renderer._received)
        self.failUnless('page_description' in renderer._received)
        self.failUnless('api' in renderer._received)
        self.failIf('terms_and_conditions' in renderer._received)
        self.failIf('accept_privacy_policy' in renderer._received)
   
    def test_handle_submit_password_mismatch(self):
        from opencore.views.validation import ValidationError
        from opencore.models.interfaces import IProfiles
        from repoze.lemonade.testing import registerContentFactory
        registerContentFactory(DummyProfiles, IProfiles)
        context = self._makeContext()
        context['profiles'] = DummyProfiles()
       
        request = self._makeRequest()
        request.method = 'POST'
        request.POST =  {'password':'1', 'password_confirm':'2',
                         'submit': u'Submit'}
        controller = self._makeOne(context, request)
        self.assertRaises(ValidationError, controller)

    def test_handle_submit_username_exists(self):
        from opencore.views.validation import ValidationError
        from opencore.models.interfaces import IProfiles
        from repoze.lemonade.testing import registerContentFactory
        registerContentFactory(DummyProfiles, IProfiles)
        context = self._makeContext()
        request = self._makeRequest()
        profiles = DummyProfiles()
        profiles['a'] = oitesting.DummyProfile()
        context['profiles'] = profiles
        controller = self._makeOne(context, request)
        request.method = 'POST'
        request.POST = {'password':'1', 'password_confirm':'1', 'username':'a'}
        self.assertRaises(ValidationError, controller)

    def test_handle_submit_success(self):
        from opencore.models.interfaces import IProfile
        from opencore.models.interfaces import IProfiles
        from repoze.lemonade.testing import registerContentFactory
        from repoze.sendmail.interfaces import IMailDelivery
        from repoze.workflow.testing import registerDummyWorkflow
        from opencore.models.interfaces import ICommunity
        from zope.interface import directlyProvides
        mailer = oitesting.DummyMailer()
        testing.registerUtility(mailer, IMailDelivery)
        registerContentFactory(oitesting.DummyProfile, IProfile)
        registerContentFactory(DummyProfiles, IProfiles)
        class DummyWhoPlugin(object):
            def remember(self, environ, identity):
                self.identity = identity
                return []
        plugin = DummyWhoPlugin()
        whoplugins = {'auth_tkt':plugin}
        request = self._makeRequest()
        request.environ['repoze.who.plugins'] = whoplugins
        community = self._makeContext()
        profiles = DummyProfiles()
        community['profiles'] = profiles
      
        community.users = oitesting.DummyUsers()
        community.members_group_name = 'community:members'
        context = testing.DummyModel()
        community['invite'] = context
        community.title = 'Community'
        community.description = 'Community'
        community.sessions = DummySessions()
        context.email = 'a@example.com'
        controller = self._makeOne(context, request)
        request.method = 'POST'
        request.POST = {
          'username': 'username',              
          'firstname' : u'Joe',
          'lastname': u'Marks',
          'description': u'',
          'biography': u"don't mess with me",
          'position': u'marksman', 
          'organization': u'xxx',
          'websites': u'noddy4.com',
          'country': u'TJ',
          'password': u'safe',
          'password_confirm': u'safe',
          'dob' : '',
          'terms': '',
          'gender': '',
          'profile.submit': u'Submit'}
        
        testing.registerDummyRenderer(
            'opencore.views:templates/email_accept_invitation.pt')
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
        self.assertEqual(len(mailer), 1)

class InviteNewUsersTests(Base):

    def _makeOne(self, context, request):
        request.api = get_template_api(context, request)
        return InviteNewUsersController(context, request)

    def _makeCommunity(self):
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

    def test_call(self):
        context = self._makeCommunity()
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
        info = controller()
        self.failUnless('api' in info)
        self.failUnless('actions' in info)
   
    def test_handle_submit_new_to_system(self):
        request = testing.DummyRequest()
        context = self._makeCommunity()
        
        registerContentFactory(DummyProfiles, IProfiles)
        context['profiles'] = profiles = DummyProfiles()
        
        mailer = self._registerMailer()
        registerCatalogSearch()
        def nonrandom(size=6):
            return 'A' * size
        testing.registerUtility(nonrandom, IRandomId)
        registerContentFactory(DummyInvitation, IInvitation)
        controller = self._makeOne(context, request)
        request.method = 'POST'
        request.POST = {
            'email_addresses': u'yo@plope.com',
            'text': u'some text',
            }

        testing.registerDummyRenderer(
            'opencore.views:templates/email_invite_new.pt')
        response = controller()
        self.assertEqual(response.location,
          'http://example.com/manage.html?status_message=One+user+invited.++'
                         )
        invitation = context['A'*6]
        self.assertEqual(invitation.email, 'yo@plope.com')
        self.assertEqual(1, len(mailer))
        self.assertEqual(mailer[0].mto, [u"yo@plope.com",])

    def test_handle_submit_already_in_system(self):
        request = testing.DummyRequest()
        context = self._makeCommunity()
        
        registerContentFactory(DummyProfiles, IProfiles)
        profiles = DummyProfiles()
        profiles['d'] = profile = oitesting.DummyProfile()
        context['profiles'] = profiles
        
        mailer = self._registerMailer()
        registerCatalogSearch()
        registerCatalogSearch(results={'email=d@x.org': [profile,]})
        def nonrandom(size=6):
            return 'A' * size
        testing.registerUtility(nonrandom, IRandomId)
        registerContentFactory(DummyInvitation, IInvitation)
        controller = self._makeOne(context, request)
        request.method = 'POST'
        request.POST = {
            'email_addresses': u'd@x.org',
            'text': u'some text',
            }
        testing.registerDummyRenderer(
            'opencore.views:templates/email_add_existing.pt')
        response = controller()
        self.assertEqual(response.location,
          'http://example.com/manage.html?status_message=One+existing+user+added+to+community.++'
                         )
        self.failIf('A'*6 in context)
        self.assertEqual(context.users.added_groups,
                         [('d', 'group:community:members')])

    def test_handle_submit_inactive_user(self):
        request = testing.DummyRequest()
        context = self._makeCommunity()
        registerContentFactory(DummyProfiles, IProfiles)
        profiles = DummyProfiles()
        profiles['e'] = profile = oitesting.DummyProfile(security_state='inactive')
        context['profiles'] = profiles
        mailer = self._registerMailer()
        registerCatalogSearch()
        registerCatalogSearch(results={'email=e@x.org': [profile,]})
        def nonrandom(size=6):
            return 'A' * size
        testing.registerUtility(nonrandom, IRandomId)
        registerContentFactory(DummyInvitation, IInvitation)
        controller = self._makeOne(context, request)
        request.method = 'POST'
        request.POST  = {
            'email_addresses': u'e@x.org',
            'text': u'some text',
            }
        testing.registerDummyRenderer(
            'opencore.views:templates/members_invite_new.pt')
        from opencore.views.validation import ValidationError
        self.assertRaises(ValidationError, controller)

    def test_handle_submit_already_in_community(self):
        request = testing.DummyRequest()
        context = self._makeCommunity()
        registerContentFactory(DummyProfiles, IProfiles)
        profiles = DummyProfiles()
        profiles['a'] = profile = oitesting.DummyProfile()
        context['profiles'] = profiles
            
       
        mailer = self._registerMailer()
        registerCatalogSearch()
        registerCatalogSearch(results={'email=a@x.org': [profile,]})
        def nonrandom(size=6):
            return 'A' * size
        testing.registerUtility(nonrandom, IRandomId)
        registerContentFactory(DummyInvitation, IInvitation)
        controller = self._makeOne(context, request)
        request.method = 'POST'
        request.POST = {
            'email_addresses': u'a@x.org',
            'text': u'some text',
            }
        response = controller()
        self.assertEqual(response.location,
          'http://example.com/manage.html?status_message=One+user+already+member.'
                         )
        self.failIf('A'*6 in context)
        self.assertEqual(context.users.added_groups, [])


class ManageMembersControllerTests(Base):

    def _makeOne(self, context, request):
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        return ManageMembersController(context, request)

    def _makeCommunity(self):
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
        context = self._makeCommunity()
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
        context = self._makeCommunity()
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
        context = self._makeCommunity()
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
        request.POST = {'remove_b' : 'True', 'remove_c' : 'True'}
        request.method = 'POST'
        self.assertRaises(ValidationError, controller)
    
    def test_handle_submit_remove_member(self):
        renderer = testing.registerDummyRenderer(
            'opencore.views:templates/members_manage.pt')
        context = self._makeCommunity()
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
        context = self._makeCommunity()
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

    ''' todo: not in view yet
    def test_handle_submit_remove_moderator(self):
        context = self._makeCommunity()
        request = testing.DummyRequest()
        controller = self._makeOne(context, request)
        converted = {'members':[{'remove':True, 'name':'b', 'resend':False,
                                 'moderator':False, 'title':'buz'}]}
        mailer = self._registerMailer()
        response = controller.handle_submit(converted)
        site = context.__parent__.__parent__
        users = site.users
        self.assertEqual(users.removed_groups, [(u'b', 'moderators')])
        self.assertEqual(len(mailer), 0)
        self.assertEqual(response.location,
                         'http://example.com/communities/community/'
                         'manage.html?status_message='
                         'Membership+information+changed%3A+'
                         'Removed+moderator+buz')'''

    def test_handle_submit_resend(self):
        testing.registerDummyRenderer(
            'opencore.views:templates/members_manage.pt')
        context = self._makeCommunity()
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
        context = self._makeCommunity()
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
        request = testing.DummyRequest(params={'val':'a'})
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
            '[{"text": "title", "id": "b"}, '
            '{"text": "title", "id": "c"}]')

'''class TestAcceptInvitationPhotoView(unittest.TestCase):
    def _callFUT(self, context, request):
        from opencore.views.members import accept_invitation_photo_view
        return accept_invitation_photo_view(context, request)

    def test_it(self):
        request = testing.DummyRequest()
        request.environ['repoze.browserid'] = '1'
        request.subpath = ('a',)
        sessions = DummySessions()
        class DummyBlob:
            def open(self, mode):
                return ('abc',)
        sessions['1'] = {'accept-invitation':
                         {'a':([('a', '1')],None, DummyBlob())}
                         }
        context = testing.DummyModel(sessions=sessions)
        response = self._callFUT(context, request)
        self.assertEqual(response.headerlist, [('a', '1')])
        self.assertEqual(response.app_iter, ('abc',))'''

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
    from repoze.bfg.testing import registerAdapter
    from zope.interface import Interface
    from opencore.models.interfaces import ICatalogSearch
    registerAdapter(dummy_search(results), (Interface,), ICatalogSearch)

class DummySessions(dict):
    def get(self, name, default=None):
        if name not in self:
            self[name] = {}
        return self[name]

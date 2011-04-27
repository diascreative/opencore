import unittest

from repoze.bfg import testing
from opencore import testing as opentesting
from opencore.testing import DummySessions
from opencore.views.api import get_template_api
from testfixtures import Replacer

class DummyForm(object):
    allfields = ()
    def __init__(self):
        self.errors = {}

profile_data = {
    'firstname': 'firstname',
    'lastname': 'lastname',
    'email': 'email@example.com',
    'phone': 'phone',
    'extension': 'extension',
    'fax': 'fax',
    'department': 'department1',
    'position': 'position',
    'organization': 'organization',
    'location': 'location',
    'country': 'CH',
    'websites': ['http://example.com'],
    'languages': 'englishy',
    'photo': None,
    'biography': 'Interesting Person',
    }

class DummyProfile(testing.DummyModel):

    def __init__(self,*args,**kw):
        testing.DummyModel.__init__(self,*args,**kw)
        self.categories={}
        
    #websites = ()
    title = 'firstname lastname'
    def __setitem__(self, name, value):
        """Simulate Folder behavior"""
        if self.get(name, None) is not None:
            raise KeyError(u"An object named %s already exists" % name)
        testing.DummyModel.__setitem__(self, name, value)

class DummyGridEntryAdapter(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

class TestEditProfileFormController(unittest.TestCase):
    simple_used = ['firstname',
                   'lastname',
                   'email',
                   'phone',
                   'extension',
                   'fax',
                   'department',
                   'position',
                   'organization',
                   'location',
                   'country',
                   'websites',
                   'languages',
                   'biography']

    def setUp(self):
        self.r = Replacer()
        # test values for author info, requiring less setup
        self.r.replace('opencore.views.people.get_author_info',
                       lambda id,request: { 
                'title'  : 'Author title',
                'country' : 'Author country',
                'organization' : 'author org',
                'url' : 'author-url',
                'photo_url' : 'author-photo-url',
                })
                       
        testing.cleanUp()
        sessions = DummySessions()
        context = DummyProfile(sessions=sessions, **profile_data)
        context.title = 'title'
        self.context = context
        request = testing.DummyRequest()
        request.environ['repoze.browserid'] = '1'
        self.request = request
        self.user_info = {'groups': set()}
        request.environ['repoze.who.identity'] = self.user_info
        request.api = get_template_api(context, request)

    def tearDown(self):
        testing.cleanUp()
        self.r.restore()

    def _makeOne(self, context, request):
        from opencore.views.people import EditProfileFormController
        return EditProfileFormController(context, request)

    def test_make_one_with_photo(self):
        context = self.context
        context['photo'] = DummyImageFile()
        controller = self._makeOne(context, self.request)
        self.failUnless(controller.photo is not None)

    def test_form_defaults(self):
        context = self.context
        request = self.request
        for fieldname, value in profile_data.items():
            if fieldname == 'photo':
                continue
            setattr(context, fieldname, value)
        controller = self._makeOne(context, request)
        defaults = controller.form_defaults()
        for fieldname, value in profile_data.items():
            self.assertEqual(defaults[fieldname], value)

    def test___call__(self):
        opentesting.registerLayoutProvider()
        from opencore.consts import countries
        renderer = testing.registerTemplateRenderer(
            'opencore.views:templates/edit_profile.pt')
        controller = self._makeOne(self.context, self.request)
        response = controller()
        self.assertEqual(renderer._received.get('form_title'), 'Edit Profile')
        self.failUnless('api' in renderer._received)
        self.assertEqual(renderer._received['api'].page_title, 'Edit title')
        self.assertEqual(renderer._received.get('include_blurb'), True)
        self.assertEqual(renderer._received.get('countries')[1:], countries)

    def test___call__user_is_staff(self):
        self.request.form = DummyForm()
        self.user_info['groups'].add('group.KarlStaff')
        opentesting.registerLayoutProvider()
        renderer = testing.registerTemplateRenderer(
            'opencore.views:templates/edit_profile.pt')
        controller = self._makeOne(self.context, self.request)
        response = controller()
        self.failUnless(renderer._received['api'].user_is_staff)
    
    def test__call__w_websites_no_dotcom(self):
        opentesting.registerLayoutProvider()
        renderer = testing.registerTemplateRenderer(
            'opencore.views:templates/edit_profile.pt')
        from webob.multidict import UnicodeMultiDict
        from opencore.testing import DummyUpload
        self.request.method = 'POST'
        self.request.POST =  UnicodeMultiDict({'profile.firstname' : u'Joe',
          'profile.lastname': u'Marks',
          'profile.description': u'',
          'profile.biography': u"don't mess with me",
          'profile.position': u'marksman', 
          'profile.organization': u'xxx',
          'profile.websites': u'noddy4.com',
          'profile.email': u'joe@example.com',
          'profile.country': u'TJ',
          'profile.password': u'',
          'profile.twitter': u'',
          'profile.facebook': u'',
          'profile.password_confirm': u'',
          'profile.submit': u'Submit'})
        
        controller = self._makeOne(self.context, self.request)
        controller()
        self.assertEqual(self.context.websites, (u'http://noddy4.com',))
       
    def test_call__w_websites_no_scheme(self):
        opentesting.registerLayoutProvider()
        renderer = testing.registerTemplateRenderer(
            'opencore.views:templates/edit_profile.pt')
        from webob.multidict import UnicodeMultiDict
        from opencore.testing import DummyUpload
        self.request.method = 'POST'
        self.request.POST =  UnicodeMultiDict({'profile.firstname' : u'Joe',
          'profile.lastname': u'Marks',
          'profile.description': u'',
          'profile.biography': u"don't mess with me",
          'profile.position': u'marksman', 
          'profile.organization': u'xxx',
          'profile.websites': 'www.happy.com',
          'profile.email': u'joe@example.com',
          'profile.country': u'TJ',
          'profile.password': u'',
          'profile.photo': None,
          'profile.twitter': u'',
          'profile.facebook': u'',
          'profile.password_confirm': u'',
          'profile.submit': u'Submit'})
        
        controller = self._makeOne(self.context, self.request)
        controller()
        self.assertEqual(self.context.websites, ('http://www.happy.com',))
        self.failIf('photo' in self.context)   
        
    def test__call__websites_error(self):
        opentesting.registerLayoutProvider()
        renderer = testing.registerTemplateRenderer(
            'opencore.views:templates/edit_profile.pt')
        from webob.multidict import UnicodeMultiDict
        self.request.method = 'POST'
        self.request.POST =  UnicodeMultiDict({'profile.firstname' : u'Joe',
          'profile.lastname': u'Marks',
          'profile.description': u'',
          'profile.biography': u"don't mess with me",
          'profile.position': u'marksman', 
          'profile.organization': u'xxx',
          'profile.websites': u'http://noddy4.com\r\nhttp://nodotcom',
          'profile.email': u'joe@example.com',
          'profile.country': u'TJ',
          'profile.photo.upload': u'',
          'profile.password': u'',
          'profile.password_confirm': u'',
          'profile.submit': u'Submit'})
        from opencore.views.validation import ValidationError
        controller = self._makeOne(self.context, self.request)
        self.assertRaises(ValidationError, controller)

    def test__call__websites_suberror(self):
        opentesting.registerLayoutProvider()
        renderer = testing.registerTemplateRenderer(
            'opencore.views:templates/edit_profile.pt')
        from webob.multidict import UnicodeMultiDict
        from opencore.testing import DummyUpload
        self.request.method = 'POST'
        self.request.POST =  UnicodeMultiDict({'profile.firstname' : u'Joe',
          'profile.lastname': u'Marks',
          'profile.description': u'',
          'profile.biography': u"don't mess with me",
          'profile.position': u'marksman', 
          'profile.organization': u'xxx',
          'profile.websites': u'http://noddy4.com\r\nhttp://nodotcom',
          'profile.email': u'joe@example.com',
          'profile.country': u'TJ',
          #'profile.photo.upload': u'',
          'profile.photo': DummyUpload(filename='test.jpg',
                                         mimetype='image/jpeg',
                                         data=one_pixel_jpeg),
          'profile.password': u'',
          'profile.password_confirm': u'',
          'profile.submit': u'Submit'})
        from opencore.views.validation import ValidationError
        controller = self._makeOne(self.context, self.request)
        try:
            controller()
        except ValidationError, err:
            self.assertEqual(err.errors['websites'].msg, u'You must provide a full domain name (like nodotcom.com)')

    """todo: once admin_edit_profile.html is sorted
    def test_admin_redirected(self):
        from webob.exc import HTTPFound
        renderer = testing.registerTemplateRenderer(
            'opencore.views:templates/edit_profile.pt')
        controller = self._makeOne(self.context, self.request)
        testing.registerDummySecurityPolicy('user', ('group.KarlAdmin',))
        response = controller()
        #print 'response=%s' % str(response)
        self.failUnless(isinstance(response, HTTPFound))
        self.assertEqual(response.location,
                'http://example.com/admin_edit_profile.html')"""

    def test_handle_submit_normal_defaults(self):
        from opencore.models.interfaces import ICommunityFile
        from opencore.testing import DummyUpload
        from repoze.lemonade.interfaces import IContentFactory
        testing.registerAdapter(lambda *arg: DummyImageFile, (ICommunityFile,),
                                IContentFactory)
        controller = self._makeOne(self.context, self.request)
        converted = {'photo': {'file' : DummyUpload(filename='test.jpg',
                                         mimetype='image/jpeg',
                                         data=one_pixel_jpeg)}
          }
        # first set up the simple fields to submit
        for fieldname, value in profile_data.items():
            if fieldname == 'photo':
                continue
            converted[fieldname] = value

        controller.handle_submit(converted)

        for fieldname, value in profile_data.items():
            if fieldname == 'photo':
                continue
            self.assertEqual(getattr(self.context, fieldname), value)
        self.failUnless('photo' in self.context)
        self.assertEqual(self.context['photo'].data, one_pixel_jpeg)

    def test_handle_submit_bad_upload(self):
        from opencore.models.interfaces import ICommunityFile
        from opencore.testing import DummyUpload
        from repoze.lemonade.interfaces import IContentFactory
        testing.registerAdapter(lambda *arg: DummyImageFile, (ICommunityFile,),
                                IContentFactory)
        controller = self._makeOne(self.context, self.request)
        converted = {'photo': {'file' : DummyUpload(filename='test.jpg',
                                         mimetype='x-application/not a jpeg',
                                         data='not a jpeg')}
          }
        # first set up the simple fields to submit
        for fieldname, value in profile_data.items():
            if fieldname == 'photo':
                continue
            converted[fieldname] = value

        from opencore.views.validation import ValidationError
        self.assertRaises(ValidationError, controller.handle_submit, converted) 
        
  

    def test_handle_submit_set_context(self):
        controller = self._makeOne(self.context, self.request)
        converted = {'websites': (u'http://noddy4.com',)}
        # first set up the simple fields to submit
        for fieldname, value in profile_data.items():
            if fieldname in ('websites', 'photo'):
                continue
            converted[fieldname] = value
        controller.handle_submit(converted)
         
        self.assertEqual(self.context.websites,  (u'http://noddy4.com',))
        for fieldname, value in profile_data.items():
            if fieldname in ('websites', 'photo'):
                continue
            self.assertEqual(getattr(self.context, fieldname), value)

    def test_handle_submit_dont_clobber_home_path(self):
        # LP #594127, bad class inheritance code caused
        # EditFormController.simple_field_names to be contaminated with field
        # names from subclasses, which was causing 'home_path' to get
        # overwritten even though it isn't shown on the form.
        controller = self._makeOne(self.context, self.request)
        # first set up the simple fields to submit
        converted = {}
        for fieldname, value in profile_data.items():
            converted[fieldname] = value
        self.context.home_path = 'foo/bar'
        controller.handle_submit(converted)
        self.assertEqual(self.context.home_path, 'foo/bar')
'''
class TestAdminEditProfileFormController(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        self.sessions = sessions = DummySessions()
        context = DummyProfile(sessions=sessions)
        context.title = 'title'
        self.context = context
        request = testing.DummyRequest()
        request.environ['repoze.browserid'] = '1'
        self.request = request
        # this initializes the available groups
        opentesting.registerSettings()

    def tearDown(self):
        testing.cleanUp()

    def _makeOne(self, context, request, active=True):
        # create the site and the users infrastructure first
        site = self.site = testing.DummyModel(sessions=self.sessions)
        site['profile'] = context
        from opencore.testing import DummyUsers
        users = self.users = site.users = DummyUsers()
        if active:
            users.add('profile', 'profile', 'password', ['group.KarlLovers'])
        from opencore.views.people import AdminEditProfileFormController
        return AdminEditProfileFormController(context, request)

    def test_form_fields(self):
        controller = self._makeOne(self.context, self.request)
        fields = dict(controller.form_fields())
        self.failUnless('login' in fields)
        self.failUnless('groups' in fields)
        self.failUnless('home_path' in fields)
        self.failUnless('password' in fields)

    def test_form_fields_inactive(self):
        controller = self._makeOne(self.context, self.request, False)
        fields = dict(controller.form_fields())
        self.failIf('login' in fields)
        self.failIf('groups' in fields)
        self.failUnless('home_path' in fields)
        self.failIf('password' in fields)

    def test_form_widgets(self):
        controller = self._makeOne(self.context, self.request)
        widgets = controller.form_widgets({})
        self.failUnless('login' in widgets)
        self.failUnless('groups' in widgets)
        self.failUnless('home_path' in widgets)
        self.failUnless('password' in widgets)

    def test_form_widgets_inactive(self):
        controller = self._makeOne(self.context, self.request, False)
        widgets = controller.form_widgets({})
        self.failIf('login' in widgets)
        self.failIf('groups' in widgets)
        self.failUnless('home_path' in widgets)
        self.failIf('password' in widgets)

    def test_form_defaults(self):
        controller = self._makeOne(self.context, self.request)
        for fieldname, value in profile_data.items():
            setattr(self.context, fieldname, value)
        context = self.context
        context.home_path = '/home_path'
        self.site.users.change_password('profile', 'password')
        self.site.users.add_user_to_group('profile', 'group.KarlLovers')
        defaults = controller.form_defaults()
        self.assertEqual(defaults['password'], '')
        self.assertEqual(defaults['home_path'], '/home_path')
        self.assertEqual(defaults['login'], 'profile')
        self.assertEqual(defaults['groups'], set(['group.KarlLovers']))
        self.assertEqual(defaults['websites'], ['http://example.com'])

    def test_form_defaults_inactive(self):
        controller = self._makeOne(self.context, self.request, False)
        for fieldname, value in profile_data.items():
            setattr(self.context, fieldname, value)
        context = self.context
        context.home_path = '/home_path'
        defaults = controller.form_defaults()
        self.failIf('password' in defaults)
        self.assertEqual(defaults['home_path'], '/home_path')
        self.failIf('login' in defaults)
        self.failIf('groups' in defaults)
        self.assertEqual(defaults['websites'], ['http://example.com'])

    def test___call__(self):
        self.request.form = DummyForm()
        controller = self._makeOne(self.context, self.request)
        opentesting.registerLayoutProvider()
        response = controller()
        self.failUnless('api' in response)
        self.assertEqual(response['api'].page_title, 'Edit title')
        self.assertEqual(response.get('form_title'),
                         'Edit User and Profile Information')
        self.assertEqual(response.get('include_blurb'), False)
        self.assertEqual(response.get('admin_edit'), True)
        self.assertEqual(response.get('is_active'), True)

    def test__call__websites_error(self):
        self.request.form = form = DummyForm()
        form.errors['websites'] = Exception("You're doing it wrong.")
        form.errors['websites.0'] = Exception("You made a boo boo.")
        opentesting.registerLayoutProvider()
        controller = self._makeOne(self.context, self.request)
        response = controller()
        self.failUnless('websites.0' in form.errors)
        self.assertEqual(
            str(form.errors['websites']), "You're doing it wrong.")

    def test__call__websites_suberror(self):
        self.request.form = form = DummyForm()
        form.errors['websites.0'] = Exception("You made a boo boo.")
        opentesting.registerLayoutProvider()
        controller = self._makeOne(self.context, self.request)
        response = controller()
        self.failIf('websites.0' in form.errors)
        self.assertEqual(
            form.errors['websites'].message, 'You made a boo boo.')

    def test___call__inactive(self):
        self.request.form = DummyForm()
        controller = self._makeOne(self.context, self.request, False)
        opentesting.registerLayoutProvider()
        response = controller()
        self.failUnless('api' in response)
        self.assertEqual(response['api'].page_title, 'Edit title')
        self.assertEqual(response.get('form_title'),
                         'Edit User and Profile Information')
        self.assertEqual(response.get('include_blurb'), False)
        self.assertEqual(response.get('admin_edit'), True)
        self.assertEqual(response.get('is_active'), False)

    def test_handle_submit_normal(self):
        from repoze.who.plugins.zodb.users import get_sha_password
        controller = self._makeOne(self.context, self.request)
        converted = {}
        converted['home_path'] = '/home_path'
        converted['password'] = 'secret'
        converted['login'] = 'newlogin'
        converted['groups'] = ['group.KarlAdmin']
        response = controller.handle_submit(converted)
        context = self.context
        self.assertEqual(context.home_path, '/home_path')
        user = self.users.get_by_id('profile')
        self.assertEqual(user['password'], get_sha_password('secret'))
        self.assertEqual(user['login'], 'newlogin')
        self.assertEqual(self.users.added_groups,
                         [('profile', 'group.KarlAdmin')])
        self.assertEqual(self.users.removed_groups,
                         [('profile', 'group.KarlLovers')])
        self.assertEqual(response.location,
                         'http://example.com/profile/'
                         '?status_message=User%20edited')

    def test_handle_submit_w_websites_no_scheme(self):
        # make sure the www. URLs get prepended
        controller = self._makeOne(self.context, self.request)
        converted = {}
        converted['home_path'] = '/home_path'
        converted['login'] = 'newlogin'
        converted['password'] = 'secret'
        converted['groups'] = ['group.KarlAdmin']
        converted['websites'] = ['www.example.com']
        controller.handle_submit(converted)
        self.assertEqual(self.context.websites, ['http://www.example.com'])

    def test_handle_submit_existing_login(self):
        # try w/ a login already in use
        from repoze.bfg.formish import ValidationError
        controller = self._makeOne(self.context, self.request)
        converted = {}
        converted['home_path'] = '/home_path'
        converted['login'] = 'inuse'
        converted['password'] = 'secret'
        converted['groups'] = ['group.KarlAdmin']
        converted['websites'] = ['www.example.com']
        context = self.context
        context['inuse'] = testing.DummyModel()
        self.assertRaises(ValidationError, controller.handle_submit,
                          converted)

    def test_handle_submit_w_login_raising_ValidationError(self):
        from repoze.bfg.formish import ValidationError
        controller = self._makeOne(self.context, self.request)
        converted = {}
        converted['home_path'] = '/home_path'
        converted['login'] = 'raise_value_error'
        converted['password'] = 'secret'
        converted['groups'] = ['group.KarlAdmin']
        converted['websites'] = ['www.example.com']
        # try again w/ special login value that will trigger ValueError
        self.assertRaises(ValidationError, controller.handle_submit,
                          converted)

    def test_handle_submit_w_websites_None(self):
        # Apparently, the formish / schemaish stuff has a bug which can give
        # us None for a sequence field.
        controller = self._makeOne(self.context, self.request)
        converted = {}
        converted['home_path'] = '/home_path'
        converted['login'] = 'newlogin'
        converted['password'] = 'secret'
        converted['groups'] = ['group.KarlAdmin']
        converted['websites'] = None
        controller.handle_submit(converted)
        self.assertEqual(self.context.websites, [])

class ShowProfileTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.people import show_profile_view
        return show_profile_view(context, request)

    def _registerTagbox(self):
        from opencore.testing import registerTagbox
        registerTagbox()

    def _registerCatalogSearch(self):
        from opencore.testing import registerCatalogSearch
        registerCatalogSearch()

    def test_editable(self):
        self._registerTagbox()
        self._registerCatalogSearch()

        from opencore.testing import DummyUsers
        testing.registerDummySecurityPolicy('userid')
        renderer = testing.registerDummyRenderer('opencore:views/templates/profile.pt')
        request = testing.DummyRequest()
        context = DummyProfile()
        context.__name__ = 'userid'
        context.users = DummyUsers()
        context.users.add("userid", "userlogin", "password", [])
        context['communities'] = testing.DummyModel()
        context['profiles'] = testing.DummyModel()
        context['profiles']['userid'] = DummyProfile()
        self._callFUT(context, request)
        self.assertEqual(len(renderer.actions), 3)
        self.assertEqual(renderer.actions[0][1], 'admin_edit_profile.html')
        self.assertEqual(renderer.actions[1][1], 'manage_communities.html')
        self.assertEqual(renderer.actions[2][1], 'manage_tags.html')

    def test_not_editable(self):
        self._registerTagbox()
        self._registerCatalogSearch()

        from opencore.testing import DummyUsers
        testing.registerDummySecurityPolicy('userid')
        renderer = testing.registerDummyRenderer('templates/profile.pt')
        request = testing.DummyRequest()
        context = DummyProfile()
        context.__name__ = 'chris'
        context.users = DummyUsers()
        context.users.add("userid", "userlogin", "password", [])
        context.users.add("chris", "chrislogin", "password", [])
        self._callFUT(context, request)
        self.assertEqual(len(renderer.actions), 1)
        self.assertEqual(renderer.actions[0][1], 'admin_edit_profile.html')
        #self.assertEqual(renderer.actions[1][1], 'delete.html')

    def test_communities(self):
        self._registerTagbox()
        self._registerCatalogSearch()

        from repoze.bfg.testing import DummyModel
        from opencore.testing import DummyCommunity
        from opencore.testing import DummyUsers
        renderer = testing.registerDummyRenderer('templates/profile.pt')
        request = testing.DummyRequest()
        context = DummyProfile()
        users = DummyUsers()

        community1 = DummyCommunity()
        community1.title = "Community 1"

        communities = community1.__parent__
        communities["community2"] = community2 = DummyCommunity()
        community2.title = "Community 2"
        users.add("userid", "userid", "password",
                  ["group.community:community:members",
                   "group.community:community2:moderators"])

        site = communities.__parent__
        site.users = users
        site["profiles"] = profiles = DummyModel()
        profiles["userid"] = context

        self._callFUT(context, request)
        self.assertEqual(renderer.communities, [
            {"title": "Community 1",
             "moderator": False,
             "url": "http://example.com/communities/community/",},
            {"title": "Community 2",
             "moderator": True,
             "url": "http://example.com/communities/community2/",},
        ])

    def test_communities_nonviewable_filtered(self):
        self._registerTagbox()
        self._registerCatalogSearch()

        from repoze.bfg.testing import DummyModel
        from repoze.bfg.testing import registerDummySecurityPolicy
        registerDummySecurityPolicy(permissive=False)
        from opencore.testing import DummyCommunity
        from opencore.testing import DummyUsers
        renderer = testing.registerDummyRenderer('templates/profile.pt')
        request = testing.DummyRequest()
        context = DummyProfile()
        users = DummyUsers()

        community1 = DummyCommunity()
        community1.title = "Community 1"

        communities = community1.__parent__
        communities["community2"] = community2 = DummyCommunity()
        community2.title = "Community 2"
        users.add("userid", "userid", "password",
                  ["group.community:community:members",
                   "group.community:community2:moderators"])

        site = communities.__parent__
        site.users = users
        site["profiles"] = profiles = DummyModel()
        profiles["userid"] = context

        self._callFUT(context, request)
        self.assertEqual(renderer.communities, [])

    def test_tags(self):
        from opencore.testing import DummyUsers
        self._registerTagbox()
        self._registerCatalogSearch()
        testing.registerDummySecurityPolicy('eddie')
        TAGS = {'beaver': 1, 'wally': 3}
        context = DummyProfile()
        context.title = "Eddie"
        context.__name__ = "eddie"
        context['communities'] = testing.DummyModel()
        context['profiles'] = testing.DummyModel()
        context['profiles']['eddie'] = DummyProfile()
        users = context.users = DummyUsers()
        users.add("eddie", "eddie", "password", [])
        tags = context.tags = testing.DummyModel()
        def _getTags(items=None, users=None, community=None):
            assert items is None
            assert list(users) == ['eddie']
            assert community is None
            return TAGS.keys()
        tags.getTags = _getTags
        def _getFrequency(tags=None, community=None, user=None):
            assert community is None
            assert tags is not None
            assert user == 'eddie'
            return TAGS.items()
        tags.getFrequency = _getFrequency
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/profile.pt')

        response = self._callFUT(context, request)

        self.assertEqual(len(renderer.tags), 2)
        self.failUnless(renderer.tags[0], {'name': 'wally', 'count': 3})
        self.failUnless(renderer.tags[1], {'name': 'beaver', 'count': 1})

    def test_tags_capped_at_ten(self):
        from opencore.testing import DummyUsers
        self._registerTagbox()
        self._registerCatalogSearch()
        testing.registerDummySecurityPolicy('eddie')
        TAGS = {'alpha': 1,
                'bravo': 2,
                'charlie': 3,
                'delta': 4,
                'echo': 5,
                'foxtrot': 6,
                'golf': 7,
                'hotel': 8,
                'india': 9,
                'juliet': 10,
                'kilo': 11,
               }
        context = DummyProfile()
        context.title = "Eddie"
        context.__name__ = "eddie"
        context['communities'] = testing.DummyModel()
        context['profiles'] = testing.DummyModel()
        context['profiles']['eddie'] = DummyProfile()
        users = context.users = DummyUsers()
        users.add("eddie", "eddie", "password", [])
        tags = context.tags = testing.DummyModel()
        def _getTags(items=None, users=None, community=None):
            assert items is None
            assert list(users) == ['eddie']
            assert community is None
            return TAGS.keys()
        tags.getTags = _getTags
        def _getFrequency(tags=None, community=None, user=None):
            assert community is None
            assert tags is not None
            assert user == 'eddie'
            return TAGS.items()
        tags.getFrequency = _getFrequency
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/profile.pt')

        response = self._callFUT(context, request)

        self.assertEqual(len(renderer.tags), 10)
        self.failUnless(renderer.tags[0], {'name': 'kilo', 'count': 11})
        self.failUnless(renderer.tags[1], {'name': 'juliet', 'count': 10})
        self.failUnless(renderer.tags[9], {'name': 'bravo', 'count': 2})

    def test_show_recently_added(self):
        self._registerTagbox()

        search_args = {}
        def searcher(context):
            def search(**args):
                search_args.update(args)
                doc1 = testing.DummyModel(title='doc1')
                doc2 = testing.DummyModel(title='doc2')
                docids = [doc1, None, doc2]
                return len(docids), docids, lambda docid: docid
            return search
        from opencore.models.interfaces import ICatalogSearch
        from repoze.bfg.testing import registerAdapter
        from zope.interface import Interface
        registerAdapter(searcher, (Interface,), ICatalogSearch)
        from opencore.models.interfaces import IGridEntryInfo
        testing.registerAdapter(DummyGridEntryAdapter, (Interface, Interface),
                                IGridEntryInfo)

        from opencore.testing import DummyUsers
        testing.registerDummySecurityPolicy('userid')
        renderer = testing.registerDummyRenderer('templates/profile.pt')
        request = testing.DummyRequest()
        context = DummyProfile()
        context.__name__ = 'chris'
        context.users = DummyUsers()
        context.users.add("userid", "userid", "password", [])
        context.users.add("chris", "chris", "password", [])
        self._callFUT(context, request)
        self.assertEqual(search_args['limit'], 5)
        self.assertEqual(search_args['creator'], 'chris')
        self.assertEqual(search_args['sort_index'], 'creation_date')
        self.assertEqual(search_args['reverse'], True)
        self.assertEqual(len(renderer.recent_items), 2)
        self.assertEqual(renderer.recent_items[0].context.title, 'doc1')
        self.assertEqual(renderer.recent_items[1].context.title, 'doc2')

    def test_system_user(self):
        self._registerTagbox()
        self._registerCatalogSearch()

        from opencore.testing import DummyUsers
        testing.registerDummySecurityPolicy('userid')
        renderer = testing.registerDummyRenderer('templates/profile.pt')
        request = testing.DummyRequest()
        context = DummyProfile()
        context.__name__ = 'admin'
        context.users = DummyUsers()
        context.users.add("userid", "userlogin", "password", [])
        context.users.add("chris", "chrislogin", "password", [])
        response = self._callFUT(context, request)
        self.assertEqual(response.status_int, 200)
        self.assertEqual(len(renderer.actions), 1)
        self.assertEqual(renderer.actions[0][1], 'admin_edit_profile.html')

    def test_never_logged_in(self):
        self._registerTagbox()
        self._registerCatalogSearch()

        from opencore.testing import DummyUsers
        renderer = testing.registerDummyRenderer('templates/profile.pt')
        request = testing.DummyRequest()
        context = DummyProfile()
        context.__name__ = 'userid'
        context.last_login_time = None
        context.users = DummyUsers()
        context.users.add("userid", "userlogin", "password", [])
        context['communities'] = testing.DummyModel()
        context['profiles'] = testing.DummyModel()
        self._callFUT(context, request)
        self.assertEqual(renderer.profile['last_login_time'], None)


class ProfileThumbnailTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.people import profile_thumbnail
        return profile_thumbnail(context, request)

    def test_wo_photo(self):
        context = testing.DummyModel()
        rsp = self._callFUT(context, testing.DummyRequest())
        self.failUnless(rsp.location.startswith('http://example.com/static/'))
        self.failUnless(rsp.location.endswith('/images/defaultUser.gif'))

    def test_w_photo(self):
        from zope.interface import directlyProvides
        from opencore.models.interfaces import IImage
        context = testing.DummyModel()
        photo = context['photo'] = testing.DummyModel()
        directlyProvides(photo, IImage)
        response = self._callFUT(context, testing.DummyRequest())
        self.assertEqual(response.location,
                         'http://example.com/photo/thumb/75x100.jpg')


class RecentContentTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.people import recent_content_view
        return recent_content_view(context, request)

    def test_without_content(self):
        context = DummyProfile()
        context.title = 'Z'
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer(
            'templates/profile_recent_content.pt')
        from opencore.testing import registerCatalogSearch
        registerCatalogSearch()
        self._callFUT(context, request)
        self.assert_(renderer.api is not None)
        self.assertEquals(len(renderer.recent_items), 0)
        self.assertFalse(renderer.batch_info['batching_required'])

    def test_with_content(self):
        search_args = {}
        def searcher(context):
            def search(**args):
                search_args.update(args)
                doc1 = testing.DummyModel(title='doc1')
                doc2 = testing.DummyModel(title='doc2')
                docids = [doc1, None, doc2]
                return len(docids), docids, lambda docid: docid
            return search
        from opencore.models.interfaces import ICatalogSearch
        from repoze.bfg.testing import registerAdapter
        from zope.interface import Interface
        registerAdapter(searcher, (Interface), ICatalogSearch)
        from opencore.models.interfaces import IGridEntryInfo
        testing.registerAdapter(DummyGridEntryAdapter, (Interface, Interface),
                                IGridEntryInfo)

        context = DummyProfile()
        context.title = 'Z'
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer(
            'templates/profile_recent_content.pt')
        self._callFUT(context, request)
        self.assert_(renderer.api is not None)
        self.assertEquals(len(renderer.recent_items), 2)
        self.assertEquals(renderer.recent_items[0].context.title, 'doc1')
        self.assertEquals(renderer.recent_items[1].context.title, 'doc2')
        self.assertFalse(renderer.batch_info['batching_required'])'''

''' could be useful later for setting alert prefs per community
class ManageCommunitiesTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

        from opencore.testing import DummyUsers

        # Set up dummy skel
        site = testing.DummyModel()
        self.users = site.users = DummyUsers()
        communities = site["communities"] = testing.DummyModel()
        community1 = communities["community1"] = testing.DummyModel()
        community1.title = "Test Community 1"
        community1.member_names = set(['a', 'c'])
        community1.moderator_names = set(['b'])
        community1.members_group_name = "community1_members"
        community1.moderators_group_name = "community1_moderators"
        self.community1 = community1

        community2 = communities["community2"] = testing.DummyModel()
        community2.title = "Test Community 2"
        community2.member_names = set(['b'])
        community2.moderator_names = set(['a', 'c'])
        community2.members_group_name = "community2_members"
        community2.moderators_group_name = "community2_moderators"
        self.community2 = community2

        community3 = communities["community3"] = testing.DummyModel()
        community3.title = "Test Community 3"
        community3.member_names = set(['b'])
        community3.moderator_names = set(['c'])
        community3.members_group_name = "community3_members"
        community3.moderators_group_name = "community3_moderators"
        self.community3 = community3

        from opencore.testing import DummyProfile
        profiles = site["profiles"] = testing.DummyModel()
        self.profile = profiles["a"] = DummyProfile()
        self.profile.alert_attachments = 'link'

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.people import manage_communities_view
        return manage_communities_view(context, request)

    def test_show_form(self):
        renderer = testing.registerDummyRenderer(
            'karl.views:templates/manage_communities.pt')
        testing.registerDummyRenderer(
            'karl.views:templates/formfields.pt')
        request = testing.DummyRequest(
            url="http://example.com/profiles/a/manage_communities.html")
        self.profile.set_alerts_preference("community2", 1)
        self._callFUT(self.profile, request)

        self.assertEqual(renderer.post_url,
            "http://example.com/profiles/a/manage_communities.html")
        self.assertEqual(2, len(renderer.communities))

        community1 = renderer.communities.pop(0)
        self.assertEqual("community1", community1["name"])
        self.assertEqual("Test Community 1", community1["title"])
        self.assertTrue(community1["alerts_pref"][0]["selected"])
        self.assertFalse(community1["alerts_pref"][1]["selected"])
        self.assertFalse(community1["alerts_pref"][2]["selected"])
        self.assertTrue(community1["may_leave"])

        community2 = renderer.communities.pop(0)
        self.assertEqual("community2", community2["name"])
        self.assertEqual("Test Community 2", community2["title"])
        self.assertFalse(community2["alerts_pref"][0]["selected"])
        self.assertTrue(community2["alerts_pref"][1]["selected"])
        self.assertFalse(community2["alerts_pref"][2]["selected"])
        self.assertFalse(community2["may_leave"])

    def test_cancel(self):
        renderer = testing.registerDummyRenderer(
            'templates/manage_communities.pt')
        request = testing.DummyRequest(
            url="http://example.com/profiles/a/manage_communities.html")

        request.params["form.cancel"] = "cancel"
        response = self._callFUT(self.profile, request)
        self.assertEqual("http://example.com/profiles/a/", response.location)

    def test_submit_alert_prefs(self):
        renderer = testing.registerDummyRenderer(
            'templates/manage_communities.pt')
        request = testing.DummyRequest(
            url="http://example.com/profiles/a/manage_communities.html")

        from opencore.models.interfaces import IProfile
        request.params["form.submitted"] = "submit"
        request.params["alerts_pref_community1"] = str(IProfile.ALERT_NEVER)
        request.params["alerts_pref_community2"] = str(IProfile.ALERT_DIGEST)

        self.assertEqual(IProfile.ALERT_IMMEDIATELY,
                         self.profile.get_alerts_preference("community1"))
        self.assertEqual(IProfile.ALERT_IMMEDIATELY,
                         self.profile.get_alerts_preference("community2"))
        response = self._callFUT(self.profile, request)

        self.assertEqual(IProfile.ALERT_NEVER,
                         self.profile.get_alerts_preference("community1"))
        self.assertEqual(IProfile.ALERT_DIGEST,
                         self.profile.get_alerts_preference("community2"))
        self.assertEqual(
            "http://example.com/profiles/a/"
            "?status_message=Community+preferences+updated.",
            response.location)

    def test_leave_community(self):
        renderer = testing.registerDummyRenderer(
            'templates/manage_communities.pt')
        request = testing.DummyRequest(
            url="http://example.com/profiles/a/manage_communities.html")

        request.params["form.submitted"] = "submit"
        request.params["leave_community1"] = "True"

        self.failUnless("a" in self.community1.member_names)
        response = self._callFUT(self.profile, request)
        self.assertEqual( [("a", "community1_members")],
                          self.users.removed_groups)
        self.assertEqual(
            "http://example.com/profiles/a/"
            "?status_message=Community+preferences+updated.",
            response.location)

    def test_leave_community_sole_moderator(self):
        renderer = testing.registerDummyRenderer(
            'templates/manage_communities.pt')
        request = testing.DummyRequest(
            url="http://example.com/profiles/a/manage_communities.html")

        request.params["form.submitted"] = "submit"
        request.params["leave_community2"] = "True"

        self.assertRaises(AssertionError, self._callFUT, self.profile, request)

    def test_set_alert_attachments_attach(self):
        request = testing.DummyRequest()
        request.params["form.submitted"] = "submit"
        request.params["attachments"] = "attach"

        self.assertEqual(self.profile.alert_attachments, "link")
        self._callFUT(self.profile, request)
        self.assertEqual(self.profile.alert_attachments, "attach")

    def test_set_alert_attachments_link(self):
        request = testing.DummyRequest()
        request.params["form.submitted"] = "submit"
        request.params["attachments"] = "link"

        self.profile.alert_attachments = "attach"
        self._callFUT(self.profile, request)
        self.assertEqual(self.profile.alert_attachments, "link")'''

class ShowProfilesViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.people import show_profiles_view
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        return show_profiles_view(context, request)

    def test_it(self):
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.adapters import CatalogSearch
        catalog = opentesting.DummyCatalog({1:'/foo', 2:'/bar'})
        testing.registerAdapter(CatalogSearch, (Interface), ICatalogSearch)
        context = testing.DummyModel()
        context.catalog = catalog
        foo = testing.DummyModel()
        testing.registerModels({'/foo':foo})
        request = testing.DummyRequest(
            params={'titlestartswith':'A'})
        renderer = testing.registerDummyRenderer('templates/profiles.pt')
        self._callFUT(context, request)
        profiles = list(renderer.profiles)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0], foo)

'''
class TestDeactivateProfileView(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.people import deactivate_profile_view
        return deactivate_profile_view(context, request)

    def test_noconfirm(self):
        context = DummyProfile(firstname='Mori', lastname='Turi')
        context.title = 'Context'
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer(
            'templates/deactivate_profile.pt')
        response = self._callFUT(context, request)
        self.assertEqual(sorted(response.keys()), ['api', 'myself'])

    def test_confirm_no_user_matching_profile(self):
        from opencore.testing import DummyUsers
        from repoze.workflow.testing import registerDummyWorkflow
        parent = testing.DummyModel()
        users = parent.users = DummyUsers()
        # Simulate a profile which has no corresponding user.
        def _raise_KeyError(name):
            users.removed_users.append(name)
            raise KeyError(name)
        users.remove = _raise_KeyError
        workflow = registerDummyWorkflow('security')
        context = DummyProfile()
        parent['userid'] = context
        testing.registerDummySecurityPolicy('admin')
        request = testing.DummyRequest(params={'confirm':'1'})

        response = self._callFUT(context, request)

        self.assertEqual(response.status, '302 Found')
        self.assertEqual(response.location,
                         'http://example.com/?status_message='
                         'Deactivated+user+account%3A+userid')
        self.assertEqual(users.removed_users, ['userid'])
        self.assertEqual(workflow.transitioned, [{
            'to_state': 'inactive', 'content': context,
            'request': request, 'guards': (),
            'context': None, 'skip_same': True}])

    def test_confirm_not_deleting_own_profile(self):
        from opencore.testing import DummyUsers
        from repoze.workflow.testing import registerDummyWorkflow
        parent = testing.DummyModel()
        users = parent.users = DummyUsers()
        workflow = registerDummyWorkflow('security')
        context = DummyProfile()
        parent['userid'] = context
        testing.registerDummySecurityPolicy('admin')
        request = testing.DummyRequest(params={'confirm':'1'})

        response = self._callFUT(context, request)

        self.assertEqual(response.status, '302 Found')
        self.assertEqual(response.location,
                         'http://example.com/?status_message='
                         'Deactivated+user+account%3A+userid')
        self.assertEqual(users.removed_users, ['userid'])
        self.assertEqual(workflow.transitioned, [{
            'to_state': 'inactive', 'content': context,
            'request': request, 'guards': (),
            'context': None, 'skip_same': True}])

    def test_confirm_deleting_own_profile(self):
        from opencore.testing import DummyUsers
        from repoze.workflow.testing import registerDummyWorkflow
        parent = testing.DummyModel()
        users = parent.users = DummyUsers()
        workflow = registerDummyWorkflow('security')
        context = DummyProfile()
        parent['userid'] = context
        testing.registerDummySecurityPolicy('userid')
        request = testing.DummyRequest(params={'confirm':'1'})

        response = self._callFUT(context, request)

        self.assertEqual(response.status, '401 Unauthorized')
        self.assertEqual(users.removed_users, ['userid'])
        self.assertEqual(workflow.transitioned, [{
            'to_state': 'inactive', 'content': context,
            'request': request, 'guards': (),
            'context': None, 'skip_same': True}])

class TestReactivateProfileView(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

        self.reset_password_calls = []

    def tearDown(self):
        testing.cleanUp()

    def _dummy_reset_password(self, user, profile, request):
        self.reset_password_calls.append((user, profile, request))

    def _callFUT(self, context, request):
        from opencore.views.people import reactivate_profile_view as fut
        return fut(context, request, self._dummy_reset_password)

    def test_noconfirm(self):
        context = DummyProfile(firstname='Mori', lastname='Turi')
        context.title = 'Context'
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer(
            'templates/reactivate_profile.pt')
        response = self._callFUT(context, request)
        self.assertEqual(sorted(response.keys()), ['api'])

    def test_confirm(self):
        from opencore.testing import DummyUsers
        from repoze.workflow.testing import registerDummyWorkflow
        parent = testing.DummyModel()
        users = parent.users = DummyUsers()
        workflow = registerDummyWorkflow('security')
        context = DummyProfile()
        parent['userid'] = context
        testing.registerDummySecurityPolicy('admin')
        request = testing.DummyRequest(params={'confirm':'1'})

        response = self._callFUT(context, request)

        self.assertEqual(response.status, '302 Found')
        self.assertEqual(response.location,
                         'http://example.com/userid/?status_message='
                         'Reactivated+user+account%3A+userid')
        self.assertEqual(users.added[0], 'userid')
        self.assertEqual(users.added[1], 'userid')
        self.assertEqual(users.added[3], [])
        self.assertEqual(workflow.transitioned, [{
            'to_state': 'active', 'content': context,
            'request': request, 'guards': (),
            'context': None, 'skip_same': True}])
        self.assertEqual(
            self.reset_password_calls,
            [(users.get_by_id('userid'), context, request)])'''

class DummyImageFile(object):
    def __init__(self, title=None, stream=None, mimetype=None, filename=None,
                 creator=None):
        self.title = title
        self.mimetype = mimetype
        if stream is not None:
            self.data = stream.read()
        else:
            self.data = one_pixel_jpeg
        self.size = len(self.data)
        self.filename= filename
        self.creator = creator
        self.is_image = mimetype != 'x-application/not a jpeg'

one_pixel_jpeg = [
0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01,
0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xff, 0xdb, 0x00, 0x43, 0x00, 0x05,
0x03, 0x04, 0x04, 0x04, 0x03, 0x05, 0x04, 0x04, 0x04, 0x05, 0x05, 0x05, 0x06,
0x07, 0x0c, 0x08, 0x07, 0x07, 0x07, 0x07, 0x0f, 0x0b, 0x0b, 0x09, 0x0c, 0x11,
0x0f, 0x12, 0x12, 0x11, 0x0f, 0x11, 0x11, 0x13, 0x16, 0x1c, 0x17, 0x13, 0x14,
0x1a, 0x15, 0x11, 0x11, 0x18, 0x21, 0x18, 0x1a, 0x1d, 0x1d, 0x1f, 0x1f, 0x1f,
0x13, 0x17, 0x22, 0x24, 0x22, 0x1e, 0x24, 0x1c, 0x1e, 0x1f, 0x1e, 0xff, 0xdb,
0x00, 0x43, 0x01, 0x05, 0x05, 0x05, 0x07, 0x06, 0x07, 0x0e, 0x08, 0x08, 0x0e,
0x1e, 0x14, 0x11, 0x14, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e, 0x1e,
0x1e, 0x1e, 0xff, 0xc0, 0x00, 0x11, 0x08, 0x00, 0x01, 0x00, 0x01, 0x03, 0x01,
0x22, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01, 0xff, 0xc4, 0x00, 0x15, 0x00,
0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x08, 0xff, 0xc4, 0x00, 0x14, 0x10, 0x01, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0xff, 0xc4, 0x00, 0x14, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xc4, 0x00,
0x14, 0x11, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xda, 0x00, 0x0c, 0x03, 0x01, 0x00,
0x02, 0x11, 0x03, 0x11, 0x00, 0x3f, 0x00, 0xb2, 0xc0, 0x07, 0xff, 0xd9
]

one_pixel_jpeg = ''.join([chr(x) for x in one_pixel_jpeg])

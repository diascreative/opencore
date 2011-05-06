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

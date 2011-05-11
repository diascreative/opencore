import unittest

from repoze.bfg import testing
from opencore import testing as opentesting
from opencore.models.interfaces import ICommunityFile
from opencore.testing import (
    DummyImageFile,
    DummySessions,
    DummyUpload,
    DummyUsers,
    one_pixel_jpeg,
    )
from opencore.views.api import get_template_api
from opencore.views.people import EditProfileFormController
from repoze.lemonade.interfaces import IContentFactory
from repoze.who.plugins.zodb.users import get_sha_password
from testfixtures import Replacer
from webob.multidict import MultiDict
class DummyForm(object):
    allfields = ()
    def __init__(self):
        self.errors = {}

profile_data = {
    'firstname': 'firstname',
    'lastname': 'lastname',
    'email': 'email@example.com',
    'position': 'position',
    'organization': 'organization',
    'country': 'CH',
    'websites': ['http://example.com'],
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
        self.r.replace('opencore.views.forms.get_current_request',
                       lambda :self.request)
        self.r.replace('opencore.views.people.authenticated_userid',
                       lambda request:'auth_user_id')
        
        testing.cleanUp()
        sessions = DummySessions()
        context = DummyProfile(sessions=sessions, **profile_data)
        context.title = 'title'
        context.__name__='admin'
        context.users = DummyUsers()
        context.users.add('admin','admin','password',())
        self.context = context
        request = testing.DummyRequest()
        request.api = get_template_api(context, request)
        request.context = context
        self.request = request

    def tearDown(self):
        testing.cleanUp()
        self.r.restore()

    def _makeOne(self):
        return EditProfileFormController(self.context, self.request)

    def test_form_defaults(self):
        context = self.context
        request = self.request
        controller = self._makeOne()
        self.assertEqual(
            controller.form_defaults(),
            {'first_name': 'firstname',
             'last_name': 'lastname',
             'details': {
                    'position': 'position',
                    'biography': 'Interesting Person',
                    'social_networks': {},
                    'organization': 'organization',
                    'country': 'CH',
                    'websites': ['http://example.com']
                    },
             'email': 'email@example.com'}
            )

    def test_get(self):
        controller = self._makeOne()
        info = controller()
        self.assertTrue('api' in info)
        self.assertTrue(info['form'].startswith('<form id="deform"'))

    def test_post_websites_no_scheme(self):
        self.request.POST =   MultiDict([
                ('first_name', u'Joe'),
                ('last_name', u'Marks'),
                ('email', u'joe@example.com'),
                ('__start__', u'details:mapping'),
                ('__start__', u'websites:sequence'),
                ('url',u'www.happy.com'),
                ('__end__', u'websites:sequence'),
                ('country', u'TJ'),
                ('__end__', u'details:mapping'),
                ('save', u'save'),
                ])
        controller = self._makeOne()
        response = controller()
        self.assertEqual(
            response.location,
            # dunno why model_url doesn't quite work here
            'http://example.comadmin/?status_message=Profile%20edited'
            )
        self.assertEqual(self.context.websites, [u'http://www.happy.com'])
        
    def test_post_websites_https(self):
        self.request.POST =   MultiDict([
                ('first_name', u'Joe'),
                ('last_name', u'Marks'),
                ('email', u'joe@example.com'),
                ('__start__', u'details:mapping'),
                ('__start__', u'websites:sequence'),
                ('url',u'https://www.happy.com'),
                ('__end__', u'websites:sequence'),
                ('country', u'TJ'),
                ('__end__', u'details:mapping'),
                ('save', u'save'),
                ])
        controller = self._makeOne()
        response = controller()
        self.assertEqual(
            response.location,
            # dunno why model_url doesn't quite work here
            'http://example.comadmin/?status_message=Profile%20edited'
            )
        self.assertEqual(self.context.websites, [u'https://www.happy.com'])
        
    def test_post_websites_error(self):
        self.request.POST =   MultiDict([
                ('first_name', u'Joe'),
                ('last_name', u'Marks'),
                ('email', u'joe@example.com'),
                ('__start__', u'details:mapping'),
                ('__start__', u'websites:sequence'),
                ('url',u'http://nodotcom'),
                ('__end__', u'websites:sequence'),
                ('country', u'TJ'),
                ('__end__', u'details:mapping'),
                ('save', u'save'),
                ])
        controller = self._makeOne()
        info = controller()
        self.failUnless('This is not a valid url' in info['form'])

    def test_post_twitter_error(self):
        # must start with @
        self.request.POST = MultiDict([
                ('first_name', u'Joe'),
                ('last_name', u'Marks'),
                ('email', u'joe@example.com'),
                ('__start__', u'details:mapping'),
                ('__start__', u'social_networks:mapping'),
                ('twitter',u'something'),
                ('__end__', u'social_networks:mapping'),
                ('country', u'TJ'),
                ('__end__', u'details:mapping'),
                ('save', u'save'),
                ])
        controller = self._makeOne()
        info = controller()
        self.failUnless(
            'This is not a valid twitter username' in info['form']
            )

    def test_handle_submit_bad_image_upload(self):
        self.request.POST = MultiDict([
                ('first_name', u'Joe'),
                ('last_name', u'Marks'),
                ('email', u'joe@example.com'),
                ('__start__', u'photo:mapping'),
                ('upload', DummyUpload(
                        filename='test.jpg',
                        mimetype='x-application/not a jpeg',
                        data='not a jpeg'
                        )),
                ('__end__', u'photo:mapping'),
                ('__start__', u'details:mapping'),
                ('country', u'TJ'),
                ('__end__', u'details:mapping'),
                ('save', u'save'),
                ])
        controller = self._makeOne()
        info = controller()
        self.failUnless(
            'This file is not an image' in info['form']
            )
        
    def test_handle_submit_minimal(self):
        # a dummy photo to check it's not overridden
        self.context['photo']=photo=testing.DummyModel()
        self.request.POST = MultiDict([
                ('first_name', u'Joe'),
                ('last_name', u'Marks'),
                ('email', u'joe@example.com'),
                ('__start__', u'details:mapping'),
                ('country', u'TJ'),
                ('__end__', u'details:mapping'),
                ('save', u'save'),
                ])
        controller = self._makeOne()
        response = controller()
        
        self.assertEqual(
            response.location,
            # dunno why model_url doesn't quite work here
            'http://example.comadmin/?status_message=Profile%20edited'
            )

        # stuff we changed
        self.assertEqual(self.context.firstname,'Joe')
        self.assertEqual(self.context.lastname,'Marks')
        self.assertEqual(self.context.email,'joe@example.com')
        self.assertEqual(self.context.country,'TJ')
        # no social stuff, none has been added
        self.assertEqual(
            tuple(self.context.categories['social'].keys()),
            ())
        # check profile image hasn't changed
        self.assertTrue(self.context['photo'] is photo)
        # check password hasn't changed
        self.assertEqual(
            self.context.users.get('admin')['password'],
            'password')
        # the following are "reset" to defaults because they
        # were missing from the form POST. Of course, this
        # can't happen in actual use ;-)
        self.assertEqual(self.context.position,'')
        self.assertEqual(self.context.organisation,'')
        self.assertEqual(self.context.biography,'')
        self.assertEqual(self.context.websites,[])
        # check modified_by is recorded
        self.assertEqual(self.context.modified_by,'auth_user_id')

    def test_handle_submit_full(self):
        testing.registerAdapter(lambda *arg: DummyImageFile,
                                (ICommunityFile,),
                                IContentFactory)
        
        self.request.POST = MultiDict([
                ('first_name', u'Ad'),
                ('last_name', u'Min'),
                ('email', u'admin@example.com'),
                ('__start__', u'password:mapping'),
                ('value', u'newpass'),
                ('confirm', u'newpass'),
                ('__end__', u'password:mapping'),
                ('__start__', u'photo:mapping'),
                ('upload', DummyUpload(filename='test.jpg',
                                       mimetype='image/jpeg',
                                       data=one_pixel_jpeg)),
                ('__end__', u'photo:mapping'),
                ('__start__', u'details:mapping'),
                ('position', u'missionary'),
                ('organisation', u'foo'),
                ('biography', u'my biog'),
                ('__start__', u'websites:sequence'),
                ('url',u'http://one.example.com'),
                ('url',u'http://two.example.com'),
                ('__end__', u'websites:sequence'),
                ('country', u'AF'),
                ('__start__', u'social_networks:mapping'),
                ('twitter', u'@mytwitter'),
                ('facebook', u'myfacebook'),
                ('__end__', u'social_networks:mapping'),
                ('__end__', u'details:mapping'), ('save', u'save'),
                ])
        controller = self._makeOne()
        response = controller()
        
        self.assertEqual(
            response.location,
            # dunno why model_url doesn't quite work here
            'http://example.comadmin/?status_message=Profile%20edited'
            )
                                      
        # stuff we changed
        self.assertEqual(self.context.firstname,'Ad')
        self.assertEqual(self.context.lastname,'Min')
        self.assertEqual(self.context.email,'admin@example.com')
        self.assertEqual(self.context.country,'AF')
        self.assertEqual(self.context.position,'missionary')
        self.assertEqual(self.context.organisation,'foo')
        self.assertEqual(self.context.biography,'my biog')
        self.assertEqual(self.context.websites,[
                    'http://one.example.com',
                    'http://two.example.com',
                    ])
        # no social stuff, none has been added
        self.assertEqual(
            self.context.categories['social']['facebook'].id,
            'myfacebook')
        self.assertEqual(
            self.context.categories['social']['twitter'].id,
            '@mytwitter')
        # check profile image
        self.assertEqual(self.context['photo'].data, one_pixel_jpeg)
        # check password has changed
        self.assertEqual(
            self.context.users.get('admin')['password'],
            get_sha_password('newpass'))
        # check modified_by is recorded
        self.assertEqual(self.context.modified_by,'auth_user_id')

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


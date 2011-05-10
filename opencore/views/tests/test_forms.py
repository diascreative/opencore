from colander import (
    MappingSchema,
    SchemaNode,
    String,
    null,
    )
from cStringIO import StringIO
from deform.widget import (
    CheckboxWidget,
    FileUploadWidget,
    Widget,
    )
from mock import Mock
from opencore.models.interfaces import ICommunityFile
from opencore.views.api import get_template_api
from opencore.views.forms import (
    AvatarWidget,
    BaseController,
    DummyTempStore,
    KarlUserWidget,
    TOUWidget,
    handle_photo_upload,
    is_image,
    valid_url,
    )
from repoze.bfg import testing
from repoze.lemonade.interfaces import IContentFactory
from testfixtures import (
    Replacer,
    ShouldRaise,
    Comparison as C,
    compare,
    )
from unittest import TestCase
from webob.exc import HTTPFound

from .test_people import (
    DummyImageFile,
    DummyProfile,
    one_pixel_jpeg,
    )

class TestDummyTempStore(TestCase):

    def setUp(self):
        self.store = DummyTempStore()
        
    def test_get(self):
        compare(
            self.store.get('x'),
            None
            )

    def test_get_default(self):
        compare(
            self.store.get('x',1),
            1
            )

    def test_getitem(self):
        with ShouldRaise(KeyError('x')):
            self.store['x']

    def test_setitem(self):
        self.store['x']=1

    def test_preview_url(self):
        compare(
            self.store.preview_url('x'),
            None
            )

class TestBaseController(TestCase):

    def setUp(self):
        self.context = testing.DummyModel()
        self.request = testing.DummyRequest()
        self.request.api = get_template_api(self.context, self.request)
        self.controller = BaseController(self.context,self.request)
        # a simple schema to test
        class Schema(MappingSchema):
            field = SchemaNode(String())
        self.controller.Schema = Schema
        # stub out the handle_submit method with mock
        self.controller.handle_submit = Mock()

    def test_api(self):
        self.assertTrue(self.controller.api is self.request.api)

    def test_data(self):
        self.assertEqual(
            self.controller.data,
            dict(api=self.request.api,
                 actions=())
            )

    def test_call_get(self):
        result = self.controller()
        self.assertTrue(result is self.controller.data)
        self.assertTrue(result['form'].startswith('<form id="deform"'))
        self.assertFalse(self.controller.handle_submit.called)

    def test_call_cancel(self):
        self.request.POST['cancel']='cancel'
        result = self.controller()
        self.assertTrue(isinstance(result,HTTPFound))
        self.assertEqual(result.location,'http://example.com/')
        self.assertFalse(self.controller.handle_submit.called)

    def test_call_save_validation_failed(self):
        self.request.POST['save']='save'
        result = self.controller()
        self.assertTrue(result is self.controller.data)
        self.assertTrue(result['form'].startswith('<form id="deform"'))
        self.assertTrue('Errors have been highlighted' in result['form'])
        self.assertFalse(self.controller.handle_submit.called)
        
    def test_call_save_okay(self):
        self.request.POST['save']='save'
        self.request.POST['field']='something'
        result = self.controller()
        self.assertTrue(
            result is self.controller.handle_submit.return_value
            )
        self.assertTrue(self.controller.handle_submit.called)

    def test_different_buttons(self):
        with Replacer() as r:
            self.controller.buttons = ('one','two')
            Form = Mock()            
            r.replace('opencore.views.forms.Form',Form)

            self.controller()

            Form.assert_called_with(
                C(SchemaNode),
                buttons = ('one','two'),
                )
            
    def test_default_form_defaults(self):
        self.assertEqual(self.controller.form_defaults(),null)
        
    def test_form_defaults(self):
        with Replacer() as r:
            self.controller.form_defaults = Mock()
            defaults = self.controller.form_defaults.return_value
            Form = Mock()
            Form.return_value = form = Mock()
            r.replace('opencore.views.forms.Form',Form)

            self.controller()

            compare(form.method_calls,[
                    ('render', (defaults,), {})
                    ])
            
    def test_call_save_different_buttons(self):
        # check that we use the last button provided
        # as the trigger to process the submit
        self.controller.buttons = ('one','two')
        self.request.POST['two']='two'
        result = self.controller()
        self.assertTrue(result is self.controller.data)
        self.assertTrue(result['form'].startswith('<form id="deform"'))
        self.assertTrue('Errors have been highlighted' in result['form'])
        self.assertFalse(self.controller.handle_submit.called)
        
class TestKarlUserWidget(TestCase):

    def setUp(self):
        self.field = Mock()
        self.field.name='users'
        self.widget = KarlUserWidget()

    def test_subclass(self):
        # assume other bits behave as per base widget :-)
        self.assertTrue(isinstance(self.widget,Widget))
                        
    def test_serialize(self):
        # call
        self.assertEqual(
            self.widget.serialize(self.field,''),
            self.field.renderer.return_value
            )
        # check we called renderer correctly
        self.field.renderer.assert_called_with(
            'karluserwidget',
            cstruct=(),
            field=self.field
            )

    def test_serialize_field_not_users(self):
        self.field.name = 'somethingelse'
        
        with ShouldRaise(Exception(
                "This widget must be used on a field named 'users'"
                )):
            self.widget.serialize(self.field,''),

        # check renderer not called
        self.assertFalse(self.field.renderer.called)

    def test_deserialize(self):
        pstruct = []

        returned = self.widget.deserialize(self.field,pstruct)

        # use identity to check we just pass through
        self.assertTrue(returned is pstruct)

class TestTOUWidget(TestCase):

    def setUp(self):
        self.field = Mock()
        self.field.name='terms_of_use'
        self.widget = TOUWidget()

    def test_subclass(self):
        # assume other bits behave as per base widget :-)
        self.assertTrue(isinstance(self.widget,CheckboxWidget))

    def test_template(self):
        self.assertEqual(self.widget.template,'terms_of_use')

class TestAvatarWidget(TestCase):

    def setUp(self):
        self.widget = AvatarWidget()

    def test_subclass(self):
        # assume other bits behave as per base widget :-)
        self.assertTrue(isinstance(self.widget,FileUploadWidget))

    def test_serialize(self):
        field = Mock()
        cstruct = Mock()
        get_current_request = Mock()
        request = get_current_request.return_value

        with Replacer() as r:
            r.replace('opencore.views.forms.get_current_request',
                      get_current_request)
            result = self.widget.serialize(field,cstruct)
            
        self.assertTrue(result is field.renderer.return_value)

        field.renderer.assert_called_with(
            'avatar',
            field=field,
            api=request.api,
            profile=request.context,
            )

class Test_handle_photo_upload(TestCase):

    # arguably should move to test_utils.py
    # once the existing handle_photo_upload is no longer used.
    def setUp(self):
        testing.cleanUp()
        testing.registerAdapter(
            lambda *arg: DummyImageFile,
            (ICommunityFile,),
            IContentFactory
            )
        self.cstruct = {
            'fp': StringIO('some image data'),
            'mimetype': 'image/jpeg',
            'filename': u'test.jpg',
            }
        self.context = DummyProfile()
        self.authenticated_userid = Mock()
        self.authenticated_userid.return_value = 'auser'
        self.r = Replacer()
        self.r.replace('opencore.views.forms.authenticated_userid',
                       self.authenticated_userid)

    def tearDown(self):
        self.r.restore()
        testing.cleanUp()
        
    def test_no_cstruct(self):
        handle_photo_upload(self.context,None,None)
        self.assertFalse(self.context.get('photo'))

    def test_no_existing_photo(self):
        handle_photo_upload(self.context,None,self.cstruct)
        content = self.context['photo']
        compare(content.title,'Photo of firstname lastname')
        compare(content.mimetype,'image/jpeg')
        compare(content.filename,'test.jpg')
        compare(content.creator,'auser')

    def test_existing_photo(self):
        self.context['photo']=testing.DummyModel()
        handle_photo_upload(self.context,None,self.cstruct)
        content = self.context['photo']
        compare(content.title,'Photo of firstname lastname')
        compare(content.mimetype,'image/jpeg')
        compare(content.filename,'test.jpg')
        compare(content.creator,'auser')

class Test_is_image(TestCase):

    def test_wrong_mimetype(self):
        compare(
            is_image(dict(mimetype='foo')),
            'This file is not an image'
            )

    def test_not_image_data(self):
        compare(
            is_image(dict(mimetype='image/jpeg',
                          fp=StringIO('foo'))),
            'This file is not an image'
            )

    def test_okay(self):
        fp = StringIO(one_pixel_jpeg)
        compare(
            is_image(dict(mimetype='image/jpeg',
                          fp=fp)),
            True
            )
        compare(fp.tell(),0)

class Test_valid_url(TestCase):

    def test_no_dotcom(self):
        compare(
            valid_url('http://nodotcom'),
            'This is not a valid url'
            )

    def test_bad_scheme(self):
        compare(
            valid_url('ftp://www.example.com'),
            'This is not a valid url',
            )

    def test_ok_no_scheme(self):
        compare(
            valid_url('www.example.com'),
            True,
            )

    def test_ok_http(self):
        compare(
            valid_url('http://www.happy.com'),
            True,
            )

    def test_ok_https(self):
        compare(
            valid_url('https://www.happy.com'),
            True,
            )

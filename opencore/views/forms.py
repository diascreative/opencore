from PIL import Image
from colander import null
from deform import (
    Form,
    ValidationFailure,
    )
from deform.widget import (
    CheckboxWidget,
    FileUploadWidget,
    Widget,
    FormWidget,
    )
from opencore.events import (
    ObjectWillBeModifiedEvent,
    ObjectModifiedEvent,
    )
from opencore.models.interfaces import (
    ICommunity,
    ICommunityFile,
    )
from opencore.utils import find_profiles
from opencore.utils import get_setting
from opencore.utilities.image import thumb_url
from pkg_resources import resource_filename
from repoze.bfg.security import (
    has_permission,
    authenticated_userid,
    )
from repoze.bfg.traversal import find_interface
from repoze.bfg.threadlocal import get_current_request
from repoze.bfg.url import model_url
from repoze.lemonade.content import create_content
from urllib import quote
from webob.exc import HTTPFound
from zope.component.event import objectEventNotify

import logging
import re

log = logging.getLogger(__name__)

### Set form template paths

default_template_path = (
        resource_filename('opencore','views/templates/widgets'),
        resource_filename('deform', 'templates')
        )
app_template_path = list(Form.default_renderer.loader.search_path)

# Append opencore and deform template paths to list of app-specific paths
for path in default_template_path:
    if path not in app_template_path:
        app_template_path.append(path)

Form.set_zpt_renderer(app_template_path)

### Helpers

class instantiate:
    """
    A class decorator to make make writing
    schemas in Controller classes easier
    """
    def __init__(self,*args,**kw):
        self.args,self.kw = args,kw
    def __call__(self,class_):
        return class_(*self.args,**self.kw)
    
def _get_manage_actions(community, request):
    # XXX - this isn't very pluggable :-(
    
    # Filter the actions based on permission in the **community**
    actions = []
    if has_permission('moderate', community, request):
        actions.append(('Manage Members', 'manage.html'))
        actions.append(('Add', 'invite_new.html'))

    return actions

class DummyTempStore:

    def get(self,name,default=None):
        return default

    def __getitem__(self,name):
        raise KeyError(name)

    def __setitem__(self,name,value):
        pass

    def __contains__(self,name):
        return False

    def preview_url(self,name):
        return None

### Controllers for form submission
    
class BaseController(object):

    buttons=('cancel','save')

    def __init__(self, context, request, form_template=None):
        self.context = context
        self.request = request
        self.form_template = form_template
        self.api = request.api
        self.data = dict(
            api=self.api,
            )
        self.data['actions']=()
        
    def __call__(self):
        self.pre_call()
        request = self.request

        form = Form(self.Schema(), buttons=self.buttons)
        if self.form_template:
            form.widget = FormWidget(template=self.form_template)

        if self.buttons[-1] in request.POST:
            controls = request.POST.items()
            log.debug('form controls: %r',controls)
            try:
                validated = form.validate(controls)
            except ValidationFailure, e:
                self.data['form']=e.render()
                return self.data
            
            return self.handle_submit(validated)
        
        elif 'cancel' in request.POST:
            
            return HTTPFound(location=self.api.here_url)

        self.data['form']=form.render(self.form_defaults())
        return self.data
    
    def pre_call(self):
        """ Called as the very first thing in the view's __call__ method.
        """

    def form_defaults(self):
        """
        Return an appstruct to populate the form.
        """
        return null
    
    def handle_submit(self, validated):
        """
        Do whatever is required with the validated data
        passed in
        """
        raise NotImplementedError()

class ContentController(BaseController):

    def handle_content(self, content, request, validated):
        """
        Do whatever is required with the validated data
        and the content object passed in
        """
        raise NotImplementedError()

    def handle_submit(self, validated):
        context = self.context
        request = self.request
        
        objectEventNotify(ObjectWillBeModifiedEvent(context))

        
        self.handle_content(context,request,validated)

        # store who modified
        context.modified_by = authenticated_userid(request)
       
        objectEventNotify(ObjectModifiedEvent(context))
        location = model_url(context, request)
        msg = '?status_message='+quote(
            context.__class__.__name__+' edited'
            )
        return HTTPFound(location=location+msg)
    
### Widgets

class KarlUserWidget(Widget):
    """
    A widget to work with the #membersearch-input magic.
    The field this is user on *must* be called 'users'.
    """

    template = 'karluserwidget'

    def serialize(self, field, cstruct, readonly=False):
        if field.name!='users':
            raise Exception(
                "This widget must be used on a field named 'users'"
                )
        # For now we don't bother with cstruct parsing.
        # If we need to use this widget for edits, then we will have to
        return field.renderer(self.template, field=field, cstruct=())

    def deserialize(self, field, pstruct):
        return pstruct
    
class TOUWidget(CheckboxWidget):

    template='terms_of_use'


class AvatarWidget(FileUploadWidget):

    template = 'avatar'
    
    def __init__(self,**kw):
        FileUploadWidget.__init__(self, None, **kw)
        self.tmpstore = DummyTempStore()

    def serialize(self, field, cstruct, readonly=False):
        # Bluegh, wish there was a better way to get
        # api and profile in here :-/
        request = get_current_request()
        return field.renderer(self.template,
                              field=field,
                              api=request.api,
                              profile=request.context)


class ImageUploadWidget(FileUploadWidget):

    template = 'image_upload'

    def __init__(self, **kw):
        FileUploadWidget.__init__(self, None, **kw)
        self.tmpstore = DummyTempStore()
        self.thumb_size = kw.get('thumb_size')

    def serialize(self, field, cstruct, readonly=False):
        if cstruct in (null, None):
            cstruct = {}
        if cstruct:
            uid = cstruct['uid']
            if not uid in self.tmpstore:
                self.tmpstore[uid] = cstruct

        template = readonly and self.readonly_template or self.template
        request = get_current_request()
        image = request.context.get(field.name)
        if image is not None:
            thumbnail_url = thumb_url(image, request, self.thumb_size or (290, 216))
        else:
            thumbnail_url = None
        return field.renderer(template, field=field, cstruct=cstruct,
                thumb_url=thumbnail_url)


### Validators

def is_image(value):
    msg = 'This file is not an image'
    if not value['mimetype'].startswith('image'):
        return msg
    fp = value['fp']
    try:
        Image.open(fp)
    except IOError:
        return msg
    fp.seek(0)
    return True

# Borrowed from:
# https://bitbucket.org/ianb/formencode/src/703c27be52b8/formencode/validators.py
# ...with modifications to make the scheme optional
url_re = re.compile(r'''
        ^((http|https)://
        (?:[%:\w]*@)?)?                           # authenticator
        (?P<domain>[a-z0-9][a-z0-9\-]{,62}\.)*  # (sub)domain - alpha followed by 62max chars (63 total)
        (?P<tld>[a-z]{2,})                      # TLD
        (?::[0-9]+)?                            # port

        # files/delims/etc
        (?P<path>/[a-z0-9\-\._~:/\?#\[\]@!%\$&\'\(\)\*\+,;=]*)?
        $
    ''', re.I | re.VERBOSE)

def valid_url(value):
    match = url_re.search(value)
    if match is not None and match.group('domain'):
       return  True
    return 'This is not a valid url'

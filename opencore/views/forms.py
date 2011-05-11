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
    )
from opencore.models.interfaces import (
    ICommunity,
    ICommunityFile,
    )
from opencore.utils import find_profiles
from opencore.utils import get_setting
from pkg_resources import resource_filename
from repoze.bfg.security import (
    has_permission,
    authenticated_userid,
    )
from repoze.bfg.traversal import find_interface
from repoze.bfg.threadlocal import get_current_request
from repoze.lemonade.content import create_content
from webob.exc import HTTPFound

import logging
import re

log = logging.getLogger(__name__)

### Set form template paths

Form.set_zpt_renderer((
        resource_filename('opencore','views/templates/widgets'),
        resource_filename('deform', 'templates'),
        ))

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

def handle_photo_upload(context, request, cstruct):
    # arguably should move to utils.py
    # once the existing handle_photo_upload is no longer used.
    if cstruct is None:
        return
    
    photo = create_content(
        ICommunityFile,
        title='Photo of ' + context.title,
        stream=cstruct['fp'],
        mimetype=cstruct['mimetype'],
        filename=cstruct['filename'],
        creator=authenticated_userid(request),
        )

    if 'photo' in context:
        del context['photo']
        
    context['photo'] = photo

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

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.api = request.api
        self.data = dict(
            api=self.api,
            )
        self.data['actions']=()
        
    def __call__(self):
        request = self.request

        form = Form(self.Schema(), buttons=self.buttons)

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

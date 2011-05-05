from colander import null
from deform import (
    Form,
    ValidationFailure,
    )
from deform.widget import (
    CheckboxWidget,
    Widget,
    )
from opencore.models.interfaces import ICommunity
from opencore.utils import find_profiles
from opencore.utils import get_setting
from pkg_resources import resource_filename
from repoze.bfg.security import has_permission
from repoze.bfg.traversal import find_interface
from webob.exc import HTTPFound

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

class BaseController(object):

    buttons=('cancel','save')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.community = find_interface(context, ICommunity)
        self.api = request.api
        self.actions = _get_manage_actions(self.community, request)
        self.profiles = find_profiles(context)
        self.system_name = get_setting(context, 'system_name', 'OpenCore')
        self.data = dict(
            api=self.api,
            actions=self.actions,
            )
        
    def __call__(self):
        request = self.request

        form = Form(self.Schema(), buttons=self.buttons)

        if self.buttons[-1] in request.POST:
            controls = request.POST.items()
            try:
                validated = form.validate(controls)
            except ValidationFailure, e:
                self.data['form']=e.render()
                return self.data
            
            return self.handle_submit(validated)
        
        elif 'cancel' in request.POST:
            
            return HTTPFound(location=self.api.here_url)

        self.data['form']=form.render()
        return self.data

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

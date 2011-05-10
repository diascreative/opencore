from repoze.bfg.view import bfg_view
from webob import Response
from formencode import Invalid
from formencode import Schema
from formencode.validators import FormValidator, FancyValidator
from formencode.validators import DateConverter
from formencode.validators import UnicodeString, OneOf, Email, StringBoolean
from formencode.validators import FieldStorageUploadConverter
from formencode.validators import FieldsMatch, RequireIfPresent, RequireIfMissing
from formencode.validators import URL, StringBool 
from formencode.foreach import ForEach
from formencode.validators import Regex
from formencode.compound import All, Pipe
from formencode.variabledecode import NestedVariables
from formencode.schema import SimpleFormValidator
from htmllaundry import sanitize
from htmllaundry.cleaners import CommentCleaner
from webob.multidict import MultiDict
from opencore.consts import countries
from opencore.views.utils import make_name
import logging

log = logging.getLogger(__name__)


class FolderName(FancyValidator):
   
    def _to_python(self, value, state):
        try:
            return make_name(state.context, value)
        except ValueError, why:
            raise Invalid(why[0], value, state)     
        
class FolderNameAvailable(FancyValidator):
   
    def _to_python(self, value, state):
        try:
            make_name(state.context, value)
            return value
        except ValueError, why:
            raise Invalid(why[0], value, state)                  

class ValidationError(Exception):
    '''
    Exception raised in views for validation errors.
    '''
    def __init__(self, controller, **errors):
        '''
        @param controller: view controller
        @param errors: error_dict normally from a formencode.Invalid 
        error dictionary raised from a compound validator (schema).
        '''
        self.errors = errors
        self.controller = controller

    def __str__(self):
        return '<ValidationError:%s>' % self.errors

def validation_error_handler(exc, request):
    '''
    General view handler setup for ValidationErrors that sets
    form errors and callbacks to the controllers make_response. 
    @param exc: ValidationError
    @param request: Request
    '''
    controller = exc.controller
    form_errors = exc.errors  
    controller.api.formerrors.update(form_errors)
    return exc.controller.make_response()
        
def safe_html(text):
    """
    Take raw html and sanitize for safe use with tal:content="structure:x"
    """
    return sanitize(text,CommentCleaner)

class SafeInput(FancyValidator):
    """ Sanitize input text
    """
    
    def _to_python(self, value, state):
        return safe_html(UnicodeString()._to_python(value, state))
    
class State(object):
    def __init__(self, **kw):
        for k,value in kw.items():
            setattr(self, k, value)

class AddForumTopicSchema(Schema):
    allow_extra_fields = True
    
    title = UnicodeString(not_empty=True, max=100)
    text = SafeInput()
           
class SignupMemberSchema(Schema):
    allow_extra_fields = True # to deal with the 'submit' field
    email_address = Email(not_empty=True)    

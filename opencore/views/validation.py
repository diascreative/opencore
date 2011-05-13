from formencode import Schema
from formencode.validators import FancyValidator
from formencode.validators import UnicodeString
from htmllaundry import sanitize
from htmllaundry.cleaners import CommentCleaner


def safe_html(text):
    """
    Take raw html and sanitize for safe use with tal:content="structure:x"
    """
    return sanitize(text,CommentCleaner)

class ValidationError(Exception):
    '''
    Exception raised in views for validation errors.
    '''
    # XXX - please don't use this for any new code!
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
    # XXX - please don't use this for any new code!
    controller = exc.controller
    form_errors = exc.errors  
    controller.api.formerrors.update(form_errors)
    return exc.controller.make_response()
        
class State(object):
    # XXX - please don't use this for any new code!
    def __init__(self, **kw):
        for k,value in kw.items():
            setattr(self, k, value)

class SafeInput(FancyValidator):
    """ Sanitize input text
    """
    
    def _to_python(self, value, state):
        return safe_html(UnicodeString()._to_python(value, state))
    
class AddForumTopicSchema(Schema):
    allow_extra_fields = True
    
    title = UnicodeString(not_empty=True, max=100)
    text = SafeInput()

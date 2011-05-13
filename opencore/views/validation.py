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

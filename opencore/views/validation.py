from repoze.bfg.view import bfg_view
from webob import Response
from formencode import Invalid
from formencode import Schema
from formencode.validators import FormValidator, FancyValidator
from formencode.validators import DateConverter, TimeConverter
from formencode.validators import UnicodeString, OneOf, Email, StringBoolean
from formencode.validators import FieldStorageUploadConverter
from formencode.validators import FieldsMatch, RequireIfPresent, RequireIfMissing
from formencode.foreach import ForEach
from formencode.compound import All, Pipe
from formencode.variabledecode import NestedVariables
from formencode.schema import SimpleFormValidator
from lxml.html import clean
from BeautifulSoup import BeautifulSoup
from webob.multidict import MultiDict
from opencore.consts import countries
import logging

log = logging.getLogger(__name__)

class SchemaFile(object):
    '''
    Basic class object for storing files (Taken from schemaish)
    '''
    def __init__(self, file, filename, mimetype, metadata=None):
        self.file = file
        self.filename = filename
        self.mimetype = mimetype
        if metadata is None:
            metadata = {}
        self.metadata = metadata

    def __repr__(self):
        return ('<schemaish.type.File file="%r" filename="%s", '
                'mimetype="%s", metadata="%r" >' % (
                    self.file, self.filename, self.mimetype, self.metadata))

class ValidationError(Exception):
    '''
    Exception raised in views for validation errors.
    '''
    def __init__(self, controller, **errors):
        self.errors = errors
        self.controller = controller

def validation_error_handler(exc, request):
    '''
    General view handler setup for ValidationErrors that sets
    form errors and callbacks to the controllers make_response. 
    @param exc: ValidationError
    @param request: Request
    '''
    try:
        controller = exc.controller
        form_errors = add_dict_prefix(controller.prefix, exc.errors)
        log.error('failed_validation handler: %s' % str(form_errors))
        controller.api.formerrors.update(form_errors)
        return exc.controller.make_response()
    except Exception, e:
         # todo: call a nicer catch all fail handler
         response = Response('User failed validation with: %s, but the '
           'vaildation_error_handler handler also failed with: %s' % (exc.errors, e)) 
         response.status_int = 500 
         return response
        
def add_dict_prefix(prefix, original_data):
    data = {}
    for k,v in original_data.items():
        data['%s%s' % (prefix,k)] = v
    return data

def remove_dict_prefix(prefix, original_data):
    new_value_dict = MultiDict()
    for k,v in original_data.items():
        if k.startswith(prefix):
            new_value_dict.add(k.replace(prefix,'',1), v)
    return new_value_dict

class PrefixSchema(Schema):
    allow_extra_fields = True
    def to_python(self, value_dict, state=None, prefix=''):
        from formencode.variabledecode import variable_decode
        data = variable_decode(remove_dict_prefix(prefix, value_dict), list_char='--')
        return super(PrefixSchema, self).to_python(data, state)
    
class PrefixedUnicodeString(UnicodeString):
    """ If a string starts with `prefix`, ignore.
        Otherwise, return `prefix` + `value`
        
            >>> v = PrefixedUnicodeString(prefix='#')
            >>> v.to_python('#foo')
            u'#foo'
            >>> v.to_python('foo')
            u'#foo'
    """
    
    prefix = ''
    
    def _to_python(self, value, state=None):
        val = super(PrefixedUnicodeString, self)._to_python(value, state)
        if not val.startswith(self.prefix):
            val = self.prefix + val
        return val

class SafeInput(FancyValidator):
    """ Sanitize input text
    """
    
    def _to_python(self, value, state):
        value = UnicodeString()._to_python(value, state)

        # - clean up the html
        value = clean.clean_html(value)

        # - extract just the text
        # XXX might remove this later, we shall use just lxml to sanitize
        #     input. However, since extracting only the text from elements is
        #     easier in BeautifulSoup, that's what I use. After we decide on
        #     what elements we should allow/disallow, we can switch to lxml.
        #       - lonetwin
        soup = BeautifulSoup(value)
        value = soup.findAll(text=True)
        value = '\n'.join(value)

        return value
    
class CommunityPreferenceSchema(PrefixSchema):
    community = UnicodeString()
    preference = OneOf(['immediately', 'digest', 'never'])

class State(object):
    def __init__(self, **kw):
        for k,value in kw.items():
            setattr(self, k, value)

class WebSitesSchema(FancyValidator):
    delimiter = '\r\n'
    
    def _to_python(self, value, state):
        return tuple([URL(add_http=True).to_python(v.strip()) for v in value.strip(self.delimiter).split(self.delimiter)])
        
   
    
        
from formencode.validators import URL, Set            
class EditProfileSchema(PrefixSchema):
    firstname = UnicodeString()
    lastname = UnicodeString()
    position = UnicodeString()
    organization = UnicodeString()
    websites = WebSitesSchema()    
    
    description = UnicodeString()
    #twitter = PrefixedUnicodeString(prefix='@')
    #facebook = UnicodeString() # todo: link
    
    email = Email(
        not_empty=True,
        messages = {
            'empty':"Please enter a valid email address",
            'badDomain':"Please enter a valid email address",
            'badUsername':"Please enter a valid email address",
            'noAt':"Please enter a valid email address",
            }
        )

    country = OneOf(countries.as_dict.keys())

    #avatar = FileUpload()

    password = UnicodeString()
    password_confirm = UnicodeString()

    chained_validators = [
        FieldsMatch(
            u'password', u'password_confirm',
            messages = {'invalidNoMatch': u'Your passwords did not match'}
        ),
    ]

    alert_preferences = ForEach(CommunityPreferenceSchema())
    pre_validators = [NestedVariables()]        
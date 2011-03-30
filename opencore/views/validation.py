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
from lxml.html import clean
from BeautifulSoup import BeautifulSoup
from webob.multidict import MultiDict
from opencore.consts import countries
from opencore.views.utils import make_name
import logging

log = logging.getLogger(__name__)


class FolderNameAvailable(FancyValidator):
   
    def _to_python(self, value, state):
        try:
            return make_name(state.context, value)
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

def validation_error_handler(exc, request):
    '''
    General view handler setup for ValidationErrors that sets
    form errors and callbacks to the controllers make_response. 
    @param exc: ValidationError
    @param request: Request
    '''
    try:
        controller = exc.controller
        if 'prefix' in controller.__dict__:
            form_errors = add_dict_prefix(controller.prefix, exc.errors)
        else:
            form_errors = exc.errors  
        log.error('failed_validation handler: %s' % str(form_errors))
        log.debug('controller.api.formdata: %s' % str(controller.api.formdata))
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

class WebSitesValidator(FancyValidator):
    delimiter = '\r\n'
     
    def _to_python(self, value, state):
        log.debug('WebSitesValidator._to_python value: %s' % value)
        return tuple([URL(add_http=True).to_python(v.strip()) for v in value.strip(self.delimiter).split(self.delimiter)])

               
class EmailAddressesValidator(FancyValidator):
    delimiter = '\r\n'

    def _to_python(self, value, state):
        log.debug('EmailAddressesValidator._to_python value: %s' % value)
        return tuple([v for v in value.strip(self.delimiter).split(self.delimiter)]) 
  
    def validate_python(self, value, state): 
        log.debug('EmailAddressesValidator.validate_python value: %s' % str(value))
        for eaddress in value:
            Email(not_empty=self.not_empty).to_python(eaddress) 

class NewMemberValidator(FancyValidator):
    messages={
            'empty' : "Please enter a username",
            'invalid' : '%(username)s is not a valid profile'
    }
  
    def validate_python(self, value, state): 
        # value is either an existing user name or list of user names 
        log.debug('NewMemberValidator.validate_python value: %s' % str(value))
        users = []
        if isinstance(value, list) or isinstance(value, tuple):
            state.user_type = 'users'
            users = value
        else:
            state.user_type = 'user'
            users.append(value)
                
        for user in users:
            if user not in state.users:
                raise Invalid(self.message('invalid', state, username=user), value, state)
       
class AddForumTopicSchema(Schema):
    allow_extra_fields = True
    
    title = UnicodeString(not_empty=True, max=100)
    text = SafeInput()
           
class InviteMemberSchema(Schema):
    # This schema accepts missing form submissions for both users and 
    # email_address. The controller checks if they are both missing
    # and raises an error against email_addresses.
    allow_extra_fields = True # to deal with the 'submit' field
    users = NewMemberValidator(not_empty=False, if_missing=None)  
    email_addresses = EmailAddressesValidator(not_empty=False, if_missing=None)    
    text = UnicodeString()  

class SignupMemberSchema(Schema):
    allow_extra_fields = True # to deal with the 'submit' field
    email_address = Email(not_empty=True)    
    
class UserNameValidator(FancyValidator):
    not_empty=True
    messages={
            'empty' : "Please enter a username",
            'invalid' : 'Username must contain only letters, numbers, and dashes',
            'taken'   : 'Username %(username)s is already taken'
    }
    
    def _to_python(self, value, state):
        log.debug('UserNameValidator._to_python value: %s' % value)
        return Regex(r'^[\w-]+$', strip=True).to_python(value, state).lower() 
    
    def validate_python(self, value, state): 
        # value is either an existing user name or list of user names 
        log.debug('UserNameValidator.validate_python value: %s' % value)
        if value in state.users:
            raise Invalid(self.message('taken', state, username=value), value, state)
  
class AcceptInvitationSchema(Schema):
    allow_extra_fields = True
    
    username = UserNameValidator()
    password = UnicodeString(not_empty=True)
    password_confirm = UnicodeString(not_empty=True)
    firstname = UnicodeString()
    lastname = UnicodeString()
    country = OneOf(countries.as_dict.keys(),
                    not_empty=True)
    
    dob = DateConverter(month_style='dd/mm/yyyy')
    gender = OneOf(('','male','female'))
    terms = StringBoolean()
    
    chained_validators = [
        FieldsMatch(
           'password', 'password_confirm',
            messages = {'invalidNoMatch': 'Your passwords did not match'}
        ),
    ]
    
       
class EditProfileSchema(PrefixSchema):
    firstname = UnicodeString()
    lastname = UnicodeString()
    position = UnicodeString()
    organization = UnicodeString()
    websites = WebSitesValidator(if_missing=())    
    
    biography = UnicodeString()    
    email = Email(not_empty=True)
    country = OneOf(countries.as_dict.keys())
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
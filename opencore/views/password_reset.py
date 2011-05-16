
# stdlib
from email.Message import Message
from uuid import uuid4

# Zope
from zope.component import getUtility

# webob
from webob.exc import HTTPFound
from webob.exc import HTTPNotFound

# Repoze
from repoze.bfg.chameleon_zpt import render_template
from repoze.bfg.url import model_url
from repoze.sendmail.interfaces import IMailDelivery

# Deform
import deform

# Colander
from colander import Email
from colander import Length
from colander import MappingSchema
from colander import SchemaNode
from colander import String

# opencore
from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IProfile
from opencore.models.password_reset import PasswordRequestRequest
from opencore.models.password_reset import REQUEST_VALIDITY_HOURS
from opencore.utils import find_users
from opencore.utils import get_setting
from opencore.views.api import TemplateAPI
from opencore.views.forms import BaseController
from opencore.views.people import min_pw_length
from opencore.views.search import SearchResultsView
from opencore.views.utils import find_site

def _get_user_by_email(context, email):
    search = ICatalogSearch(context)
    q = dict(interfaces=[IProfile], email={'query': email})
    num, docids, resolver = search(**q)
    user = [resolver(docid) for docid in docids]
    user = user[0] if user else None
    
    return user

class ResetRequestSchema(object):
    class _Schema(MappingSchema):
        email = SchemaNode(String(), title='e-mail', description='Enter your e-mail',
                           validator=Email())

    def Schema(self):
        s = self._Schema().clone()
        return s
    
class ResetConfirmSchema(object):
    class _Schema(MappingSchema):
        password = SchemaNode(String(), title='password1', description='Enter new password',
                           validator=Length(min=min_pw_length(), max=100), 
                           widget=deform.widget.CheckedPasswordWidget(size=20))
        
        request_id = SchemaNode(String(), title='request_id', 
                                widget=deform.widget.HiddenWidget())
        

    def Schema(self):
        s = self._Schema().clone()
        return s

class ResetRequestView(ResetRequestSchema, BaseController):
    
    def __init__(self, context, request):
        super(ResetRequestView, self).__init__(context, request)
        self.context = context
        self.request = request
        
    def _redirect(self):
        location = model_url(self.context, self.request, 
            query={'status_message': "We've sent you the instructions, check e-mail"})
        return HTTPFound(location=location)

    def handle_submit(self, validated):
        
        user = _get_user_by_email(self.context, validated['email'])
        
        # No such user, we're not letting anyone know about it though to protect
        # users from crooks trying to explore the users DB in hope of finding
        # out who has an account here.
        if not user:
            return self._redirect()
        
        request_id = uuid4().hex
        request = PasswordRequestRequest(request_id, user.email)
        
        site = find_site(self.context)
        if user.email in site['reset_password']:
            del site['reset_password'][user.email]
            
        site['reset_password'][user.email] = request

        reset_url = model_url(self.context, self.request, 
                              "reset.html", query=dict(key=request_id))
        
        # send email
        mail = Message()
        system_name = get_setting(self.context, 'system_name', 'OpenCore')
        admin_email = get_setting(self.context, 'admin_email')
        mail["From"] = "%s Administrator <%s>" % (system_name, admin_email)
        mail["To"] = "%s <%s>" % (user.title, user.email)
        mail["Subject"] = "%s Password Reset Request" % system_name
        body = render_template(
            "templates/email_reset_password.pt",
            login=user.__name__,
            reset_url=reset_url,
            system_name=system_name,
            valid_hours=REQUEST_VALIDITY_HOURS,
        )
    
        if isinstance(body, unicode):
            body = body.encode("UTF-8")
    
        mail.set_payload(body, "UTF-8")
        mail.set_type("text/html")
    
        recipients = [user.email]
        mailer = getUtility(IMailDelivery)
        mailer.send(admin_email, recipients, mail)
        
        return self._redirect()
    
class ResetConfirmView(ResetConfirmSchema, BaseController):
    
    def __init__(self, context, request):
        super(ResetConfirmView, self).__init__(context, request)
        self.context = context
        self.request = request
        
    def form_defaults(self):
        return {'request_id': self.request.params.get('key', '')}
        
    def _get_email_by_request_id(self, request_id):
        site = find_site(self.context)
        for email in site['reset_password']:
            request = site['reset_password'][email]
            if request.request_id == request_id:
                return request.email
        else:
            return None
        
    def pre_call(self):
        request_id = self.request.params.get('key', None)
        if not request_id:
            request_id = self.request.POST.get('key', None)
            
        if not request_id:
            raise Exception("Could not find the 'key' parameter")
        
        email = self._get_email_by_request_id(request_id)
        if not email:
            raise Exception("No such key [%s]" % request_id)
        
    def _redirect(self):
        location = model_url(self.context, self.request,
                             query={'status_message':'Your password has been changed'})
        return HTTPFound(location=location)
    
    def handle_submit(self, validated):
        email = self._get_email_by_request_id(validated['request_id'])
        user = _get_user_by_email(self.context, email)
        
        users = find_users(self.context)
        users.change_password(user.__name__, validated['password'])
        
        site = find_site(self.context)
        del site['reset_password'][user.email]
        
        return self._redirect()
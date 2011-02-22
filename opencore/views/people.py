import uuid
import logging
import random
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1
import datetime
from email.Message import Message

from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.chameleon_zpt import render_template
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import effective_principals
from repoze.bfg.security import has_permission
from repoze.bfg.url import model_url
from repoze.sendmail.interfaces import IMailDelivery
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component.event import objectEventNotify
import formencode
from webob.exc import HTTPFound
from webob import Response
from opencore.events import ObjectWillBeModifiedEvent
from opencore.events import ObjectModifiedEvent
from opencore.consts import countries
from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IGridEntryInfo
from opencore.models.interfaces import IContent
from opencore.models.interfaces import IProfile
from opencore.utilities.image import thumb_url
from opencore.utils import find_communities
from opencore.utils import find_tags
from opencore.utils import find_users
from opencore.utils import find_site
from opencore.utils import find_profiles
from opencore.utils import get_layout_provider
from opencore.utils import get_setting
from opencore.security.policy import to_profile_active
from opencore.security.policy import to_profile_inactive

from opencore.views.communities import get_preferred_communities
from opencore.views.communities import get_my_communities
from opencore.views.tags import get_tags_client_data
from opencore.views.utils import convert_to_script
from opencore.views.utils import handle_photo_upload
from opencore.views.utils import Invalid
from opencore.views.api import TemplateAPI
from opencore.views.batch import get_catalog_batch
from opencore.views.validation import SchemaFile
from opencore.views.validation import EditProfileSchema
from opencore.views.validation import add_dict_prefix
from opencore.views.validation import ValidationError


log = logging.getLogger(__name__)
PROFILE_THUMB_SIZE = (75, 100)
_MIN_PW_LENGTH = None
max_reset_timedelta = datetime.timedelta(3)  # days

def min_pw_length():
    global _MIN_PW_LENGTH
    if _MIN_PW_LENGTH is None:
        _MIN_PW_LENGTH = get_setting(None, 'min_pw_length', 8)
    return _MIN_PW_LENGTH

def show_profiles_view(context, request):
    system_name = get_setting(context, 'system_name', 'OpenCore')
    page_title = '%s Profiles' % system_name
    api = TemplateAPI(context, request, page_title)

    # Grab the data for the two listings, main communities and portlet
    search = ICatalogSearch(context)

    query = dict(sort_index='title', interfaces=[IProfile], limit=5)

    titlestartswith = request.params.get('titlestartswith')
    if titlestartswith:
        query['titlestartswith'] = (titlestartswith, titlestartswith)

    num, docids, resolver = search(**query)

    profiles = []
    for docid in docids:
        model = resolver(docid)
        if model is None:
            continue
        profiles.append(model)

    return render_template_to_response(
        'templates/profiles.pt',
        api=api,
        profiles=profiles,
        )


def show_profile_view(context, request):
    """Show a profile with actions if the current user"""
    page_title = 'View Profile'
    api = TemplateAPI(context, request, page_title)
    
    # Create display values from model object
    profile = {}
    for name in [name for name in context.__dict__.keys()
                 if not name.startswith("_")]:
        profile_value = getattr(context, name)
        if profile_value is not None:
            # Don't produce u'None'
            profile[name] = unicode(profile_value)
        else:
            profile[name] = None

    if 'fax' not in profile:
        profile['fax'] = '' # BBB

    # 'websites' is a property, so the loop above misses it
    profile["websites"] = context.websites

    # ditto for 'title'
    profile["title"] = context.title

    if profile.has_key("languages"):
        profile["languages"] = context.languages

    if profile.has_key("department"):
        profile["department"] = context.department

    if profile.get("last_login_time"):
        stamp = context.last_login_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        profile["last_login_time"] = stamp

    if profile.has_key("country"):
        # translate from country code to country name
        country_code = profile["country"]
        country = countries.as_dict.get(country_code, u'')
        profile["country"] = country

    # Display portrait
    photo = context.get('photo')
    display_photo = {}
    if photo is not None:
        display_photo["url"] = thumb_url(photo, request, PROFILE_THUMB_SIZE)
    else:
        display_photo["url"] = api.static_url + "/images/defaultUser.gif"
    profile["photo"] = display_photo

    # provide client data for rendering current tags in the tagbox
    client_json_data = dict(
        tagbox = get_tags_client_data(context, request),
        )

    # Get communities this user is a member of, along with moderator info
    #
    communities = {}
    communities_folder = find_communities(context)
    user_info = find_users(context).get_by_id(context.__name__)
    if user_info is not None:
        for group in user_info["groups"]:
            if group.startswith("group.community:"):
                unused, community_name, role = group.split(":")
                if (communities.has_key(community_name) and
                    role != "moderators"):
                    continue

                community = communities_folder.get(community_name, None)
                if community is None:
                    continue

                if has_permission('view', community, request):
                    communities[community_name] = {
                        "title": community.title,
                        "moderator": role == "moderators",
                        "url": model_url(community, request),
                    }

    communities = communities.values()
    communities.sort(key=lambda x:x["title"])

    preferred_communities = []
    my_communities = None
    name = context.__name__
    # is this the current user's profile?
    if authenticated_userid(request) == name:
        preferred_communities = get_preferred_communities(communities_folder,
                                                          request)
        my_communities = get_my_communities(communities_folder, request)

    tagger = find_tags(context)
    if tagger is None:
        tags = ()
    else:
        tags = []
        names = tagger.getTags(users=[context.__name__])
        for name, count in sorted(tagger.getFrequency(names,
                                                      user=context.__name__),
                                  key=lambda x: x[1],
                                  reverse=True,
                                 )[:10]:
            tags.append({'name': name, 'count': count})

    # List recently added content
    num, docids, resolver = ICatalogSearch(context)(
        sort_index='creation_date', reverse=True,
        interfaces=[IContent], limit=5, creator=context.__name__,
        allowed={'query': effective_principals(request), 'operator': 'or'},
        )
    recent_items = []
    for docid in docids:
        item = resolver(docid)
        if item is None:
            continue
        adapted = getMultiAdapter((item, request), IGridEntryInfo)
        recent_items.append(adapted)
   
    return render_template_to_response(
        'templates/profile.pt',
        api=api,
        profile=profile,
        actions=get_profile_actions(context, request),
        photo=photo,
        head_data=convert_to_script(client_json_data),
        communities=communities,
        my_communities=my_communities,
        preferred_communities=preferred_communities,
        tags=tags,
        recent_items=recent_items
        )

def profile_thumbnail(context, request):
    api = TemplateAPI(context, request, 'Profile thumbnail redirector')
    photo = context.get('photo')
    if photo is not None:
        url = thumb_url(photo, request, PROFILE_THUMB_SIZE)
    else:
        url = api.static_url + "/images/defaultUser.gif"
    return HTTPFound(location=url)

def get_profile_actions(profile, request):
    actions = []
    same_user = (authenticated_userid(request) == profile.__name__)
    if has_permission('administer', profile, request):
        actions.append(('Edit', 'admin_edit_profile.html'))
    elif same_user:
        actions.append(('Edit', 'edit_profile.html'))
    if same_user:
        actions.append(('Manage Communities', 'manage_communities.html'))
        actions.append(('Manage Tags', 'manage_tags.html'))
    return actions

class EditProfileFormController(object):
    """
    Controller for the profile edit form.  Also the base class
    for the controllers for the admin profile edit and add user forms.
    """
    simple_field_names = [
        "firstname",
        "lastname",
        "email",
        "phone",
        "extension",
        "fax",
        "department",
        "position",
        "organization",
        "location",
        "country",
        "websites",
        "languages",
        "office",
        "room_no",
        "biography",
    ]

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.page_title = "Edit %s" % context.title
        self.api = TemplateAPI(self.context, self.request, self.page_title)
        layout_provider = get_layout_provider(self.context, self.request)
        self.layout = layout_provider('generic')
        self.form_title = 'Edit Profile'
        self.prefix = 'profile.'
        
        photo = context.get('photo')
        if photo is not None:
            photo = SchemaFile(None, photo.__name__, photo.mimetype)
        self.photo = photo

    def form_defaults(self):
        context = self.context
        defaults = {'firstname': context.firstname,
                    'lastname': context.lastname,
                    'email': context.email,
                    'phone': context.phone,
                    'extension': context.extension,
                    'fax': context.fax,
                    'department': context.department,
                    'position': context.position,
                    'organization': context.organization,
                    'location': context.location,
                    'country': context.country,
                    'websites': context.websites,
                    'languages': context.languages,
                    'photo': self.photo,
                    'biography': context.biography,
                    }
        return defaults

    def __call__(self):
               
        self.api.formdata = add_dict_prefix(self.prefix, self.form_defaults())
        log.debug('api.formdata: %s' % str(self.api.formdata))
       
        if self.api.user_is_admin:
            log.debug('user_is_admin so redirecting to admin_edit_profile.html.')
            return HTTPFound(location=model_url(self.context,
                self.request, 'admin_edit_profile.html'))

        if self.request.method == 'POST':
            post_data = self.request.POST
            log.debug('request.POST: %s' % post_data)
            try:
                # validate and convert
                self.api.formdata = EditProfileSchema.to_python(post_data, state=None, prefix='profile.')
            except formencode.Invalid, e:
                self.api.formdata = post_data
                raise ValidationError(self, **e.error_dict)
            else:
                return self.handle_submit(self.api.formdata)
        
        return self.make_response()
        
    def make_response(self):
        result = render_template(
                       'templates/edit_profile.pt',
                       api=self.api, actions=(), layout=self.layout,
                       form_title=self.form_title, include_blurb=True,
                       countries=[('', 'Select your Country')] + countries,
                       challenges=[],
                       preferences= ['immediately', 'digest', 'never'],
                       defaults=[])     
        return Response(body=result, content_type='text/html')               
       
    def handle_submit(self, converted):
        context = self.context
        request = self.request
        log.debug('handle_submit: %s' % str(converted))
        objectEventNotify(ObjectWillBeModifiedEvent(context))
        # Handle the easy ones
        for name in self.simple_field_names:
            if name in converted:
                 log.debug('setting profile.%s=%s' % (name, converted.get(name)))
                 setattr(context, name, converted.get(name))
            else:
                log.warn('profile attribute name=%s was not included in form post data?' % name)     
        # Handle the picture and clear the temporary filestore
        try:
            handle_photo_upload(context, converted)
        except Invalid, e:
            raise ValidationError(self, **e.error_dict)
        context.modified_by = authenticated_userid(request)
        # Emit a modified event for recataloging
        objectEventNotify(ObjectModifiedEvent(context))
        # Whew, we made it!
        path = model_url(context, request)
        msg = '?status_message=Profile%20edited'
        return HTTPFound(location=path+msg)
    
class AdminEditProfileFormController(EditProfileFormController):
    """
    Extends the default profile edit controller w/ all of the extra
    logic that the admin form requires.
    """
    simple_field_names = EditProfileFormController.simple_field_names
    simple_field_names = simple_field_names + ['home_path']

    def __init__(self, context, request):
        super(AdminEditProfileFormController, self).__init__(context, request)
        self.users = find_users(context)
        self.userid = context.__name__
        self.user = self.users.get_by_id(self.userid)
        if self.user is not None:
            self.is_active = True
            self.user_groups = set(self.user['groups'])
            self.group_options = get_group_options(self.context)
        else:
            self.is_active = False
        self.form_title = 'Edit User and Profile Information'    
  
    def form_defaults(self):
        defaults = super(AdminEditProfileFormController, self).form_defaults()
        context = self.context
        if self.user is not None:
            defaults.update({'login': self.user['login'],
                             'groups': self.user_groups,
                             'password': ''})
        defaults['home_path'] = context.home_path
        return defaults
     
    def __call__(self):
               
        self.api.formdata = add_dict_prefix(self.prefix, self.form_defaults())
        log.debug('api.formdata: %s' % str(self.api.formdata))
       
        if self.request.method == 'POST':
            post_data = self.request.POST
            log.debug('AdminEditProfileFormController request.POST: %s' % post_data)
            try:
                # validate and convert
                self.api.formdata = EditProfileSchema.to_python(post_data, state=None, prefix='profile.')
            except formencode.Invalid, e:
                self.api.formdata = post_data
                raise ValidationError(self, **e.error_dict)
            else:
                return self.handle_submit(self.api.formdata)
        
        return self.make_response()
    
    def make_response(self):
        result = render_template(
                       'templates/edit_profile.pt',
                       api=self.api, actions=(), layout=self.layout,
                       form_title=self.form_title, include_blurb=False,
                       admin_edit=True,  is_active=self.is_active, 
                       countries=[('', 'Select your Country')] + countries,
                       challenges=[],
                       preferences= ['immediately', 'digest', 'never'],
                       defaults=[])     
        return Response(body=result, content_type='text/html')   
    
    def handle_submit(self, converted):
        context = self.context
        request = self.request
        users = self.users
        userid = self.userid
        user = self.user
        '''if user is not None:
            # todo: login is not in the converted map, investigate use of this admin edit form
            login = converted.get('login')
            login_changed = users.get_by_login(login) != user
            if (login_changed and
                (users.get_by_id(login) is not None or
                 users.get_by_login(login) is not None or
                 login in context)):
                msg = "Login '%s' is already in use" % login
                raise ValidationError(login=msg)
        objectEventNotify(ObjectWillBeModifiedEvent(context))
        if user is not None:
            # Set new login
            try:
                users.change_login(userid, converted['login'])
            except ValueError, e:
                raise ValidationError(login=str(e))
            # Set group memberships
            user_groups = self.user_groups
            chosen_groups = set(converted['groups'])
            for group, group_title in self.group_options:
                if group in chosen_groups and group not in user_groups:
                    users.add_user_to_group(userid, group)
                if group in user_groups and group not in chosen_groups:
                    users.remove_user_from_group(userid, group)
            # Edit password
            if converted.get('password', None):
                users.change_password(userid, converted['password'])'''
        # Handle the easy ones
        for name in self.simple_field_names:
            setattr(context, name, converted.get(name))
        # Handle the picture and clear the temporary filestore
        try:
            handle_photo_upload(context, converted)
        except Invalid, e:
            raise ValidationError(self, **e.error_dict)
        #self.filestore.clear()
        context.modified_by = authenticated_userid(request)
        # Emit a modified event for recataloging
        objectEventNotify(ObjectModifiedEvent(context))
        # Whew, we made it!
        path = model_url(context, request)
        msg = '?status_message=User%20edited'
        return HTTPFound(location=path+msg)    

def get_group_options(context):
    group_options = []
    for group in get_setting(context, "selectable_groups").split():
        if group.startswith('group.'):
            title = group[6:]
        else:
            title = group
        group_options.append((group, title))
    return group_options


def recent_content_view(context, request):
    batch = get_catalog_batch(context, request,
        sort_index='creation_date', reverse=True,
        interfaces=[IContent], creator=context.__name__,
        allowed={'query': effective_principals(request), 'operator': 'or'},
        )

    recent_items = []
    for item in batch['entries']:
        adapted = getMultiAdapter((item, request), IGridEntryInfo)
        recent_items.append(adapted)

    page_title = "Content Added Recently by %s" % context.title
    api = TemplateAPI(context, request, page_title)
    return render_template_to_response(
        'templates/profile_recent_content.pt',
        api=api,
        batch_info=batch,
        recent_items=recent_items,
        )

def request_password_reset(user, profile, request):
    profile.password_reset_key = sha1(
        str(random.random())).hexdigest()
    profile.password_reset_time = datetime.datetime.now()
    context = find_site(profile)
    reset_url = model_url(
        context, request, "reset_confirm.html",
        query=dict(key=profile.password_reset_key))

    # send email
    mail = Message()
    system_name = get_setting(context, 'system_name', 'OpenCore')
    admin_email = get_setting(context, 'admin_email')
    mail["From"] = "%s Administrator <%s>" % (system_name, admin_email)
    mail["To"] = "%s <%s>" % (profile.title, profile.email)
    mail["Subject"] = "%s Password Reset Request" % system_name
    body = render_template(
        "templates/email_reset_password.pt",
        login=user['login'],
        reset_url=reset_url,
        system_name=system_name,
    )

    if isinstance(body, unicode):
        body = body.encode("UTF-8")

    mail.set_payload(body, "UTF-8")
    mail.set_type("text/html")

    recipients = [profile.email]
    mailer = getUtility(IMailDelivery)
    mailer.send(admin_email, recipients, mail)
    
def deactivate_profile_view(context, request):
    name = context.__name__
    myself = authenticated_userid(request) == context.__name__

    confirm = request.params.get('confirm')
    if confirm:
        try:
            find_users(context).remove(name)
        except KeyError:
            pass
        to_profile_inactive(context)
        if myself:
            return logout_view(context, request, reason='User removed')
        query = {'status_message': 'Deactivated user account: %s' % name}
        parent = context.__parent__
        location = model_url(parent, request, query=query)

        return HTTPFound(location=location)

    page_title = 'Deactivate user account for %s %s' % (context.firstname,
                                                        context.lastname)
    api = TemplateAPI(context, request, page_title)

    # Show confirmation page.
    return dict(api=api, myself=myself)

def reactivate_profile_view(context, request,
                            reset_password=request_password_reset):
    name = context.__name__
    confirm = request.params.get('confirm')
    if confirm:
        users = find_users(context)
        temp_passwd = str(uuid.uuid4())
        users.add(name, name, temp_passwd, [])
        to_profile_active(context)
        reset_password(users.get_by_id(name), context, request)
        query = {'status_message': 'Reactivated user account: %s' % name}
        location = model_url(context, request, query=query)

        return HTTPFound(location=location)

    page_title = 'Reactivate user account for %s %s' % (context.firstname,
                                                        context.lastname)
    api = TemplateAPI(context, request, page_title)

    # Show confirmation page.
    return dict(api=api)

class ResetConfirmController(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.api = TemplateAPI(self.context, self.request, 'Reset Password')

    '''def form_fields(self):
        fields = [('login', login_field),
                  ('password', password_field),
                  ]
        return fields

    def form_widgets(self, fields):
        widgets = {'login': formish.Input(empty=''),
                   'password': karlwidgets.KarlCheckedPassword()}
        return widgets'''

    def __call__(self):
        key = self.request.params.get('key')
        if not key or len(key) != 40:
            self.api.page_title = 'Password Reset URL Problem'
            return render_template_to_response('templates/reset_failed.pt',
                                               api=api)
            
            
        if self.request.method == 'POST':
            post_data = self.request.POST
            log.debug('request.POST: %s' % post_data)
            try:
                # todo: validate and convert
                pass
            except formencode.Invalid, e:
                self.api.formdata = post_data
                raise ValidationError(self, **e.error_dict)
            else:
                return self.handle_submit(self.api.formdata)
        
        return self.make_response()
        
    def make_response(self):
        #snippets = get_template('forms/templates/snippets.pt')
        #snippets.doctype = xhtml
        #blurb_macro = snippets.macros['reset_confirm_blurb']
        return render_template_to_response('templates/reset_confirm.pt',
                                           api=self.api,
                                           blurb_macro='',
                                           post_url=self.request.url,
                                           formprefix='')
       

    def handle_submit(self, converted):
        try:
            context = self.context
            request = self.request
            key = request.params.get('key')
            if not key or len(key) != 40:
                e = ResetFailed()
                e.page_title = 'Password Reset URL Problem'
                raise e
            users = find_users(context)
            user = users.get_by_login(converted['login'])
            if user is None:
                raise ValidationError(login='No such user account exists')
            userid = user.get('id')
            if userid is None:
                userid = user['login']

            profiles = find_profiles(context)
            profile = profiles.get(userid)
            if profile is None:
                raise ValidationError(login='No such profile exists')

            if key != getattr(profile, 'password_reset_key', None):
                e = ResetFailed()
                e.page_title = 'Password Reset Confirmation Problem'
                raise e

            now = datetime.datetime.now()
            t = getattr(profile, 'password_reset_time', None)
            if t is None or now - t > max_reset_timedelta:
                e = ResetFailed()
                e.page_title = 'Password Reset Confirmation Key Expired'
                raise e

            # The key matched.  Clear the key and reset the password.
            profile.password_reset_key = None
            profile.password_reset_time = None
            password = converted['password'].encode('UTF-8')
            users.change_password(userid, password)

            page_title = 'Password Reset Complete'
            api = TemplateAPI(context, request, page_title)
            return render_template_to_response(
                'templates/reset_complete.pt',
                api=api,
                login=converted['login'],
                password=converted['password'],
                )

        except ResetFailed, e:
            api = TemplateAPI(context, request, e.page_title)
            return render_template_to_response('templates/reset_failed.pt',
                                               api=api)

class ResetFailed(Exception):
    pass

import uuid
import logging
import random
try:
    from hashlib import sha1
except ImportError:
    from sha import new as sha1
import datetime
from email.Message import Message

from colander import (
    Email,
    Function,
    MappingSchema,
    Regex,
    SchemaNode,
    SequenceSchema,
    String,
    )
from deform import FileData
from deform.widget import (
    CheckedPasswordWidget,
    SelectWidget,
    TextAreaWidget,
    )

from repoze.bfg.traversal import model_path
from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.chameleon_zpt import render_template
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import effective_principals
from repoze.bfg.security import has_permission
from repoze.bfg.url import model_url
from repoze.bfg.view import bfg_view
from repoze.sendmail.interfaces import IMailDelivery
from zope.component import getMultiAdapter
from zope.component import getUtility
from webob.exc import HTTPFound
from opencore.consts import countries
from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IGridEntryInfo
from opencore.models.interfaces import IContent
from opencore.models.interfaces import IProfile
from opencore.models.interfaces import IProfileDict
from opencore.models.profile import SocialCategory
from opencore.models.profile import SocialCategoryItem
from opencore.models.profile import social_category
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
from opencore.views.forms import (
    AvatarWidget,
    ContentController,
    instantiate,
    is_image,
    valid_url,
    )
from opencore.views.tags import get_tags_client_data
from opencore.views.utils import (
    comments_to_display,
    convert_to_script,
    get_author_info,
    handle_photo_upload,
    )
from opencore.views.api import TemplateAPI
from opencore.views.batch import get_catalog_batch
from opencore.utilities.interfaces import IAppDates
from opencore.views.batch import get_catalog_batch_grid


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
    api = request.api
    api.page_title = page_title

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

def get_profile_actions(profile,request):
    # XXX - this should probably be a utility to aid overriding!
    actions = {}
    same_user = (authenticated_userid(request) == profile.__name__)
    is_admin = has_permission('administer', profile, request)

    if same_user or is_admin:
        actions['edit'] = model_url(profile, request, 'edit_profile.html')

        actions['manage_communities'] = model_url(profile, request,
                                                  'manage_communities.html')

        actions['manage_tags'] = model_url(profile, request,
                                           'manage_tags.html')
        actions['manage_bookmarks'] = model_url(profile, request,
                                                'manage_bookmarks.html')
        actions['mailbox'] = model_url(profile, request,
                                                'mailbox.html')
    actions['feed'] = model_url(profile, request, 'contentfeed.html')

    return actions

class ShowProfileView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.api = TemplateAPI(self.context, self.request,
                               "View %s" % context.title)
        layout_provider = get_layout_provider(self.context, self.request)
        self.layout = layout_provider('generic')
        self.photo_thumb_size = (220,150)

    def __call__(self):

        profile_details = getUtility(IProfileDict, name='profile-details')
        profile_details.update_details(self.context, self.request, self.api,
                                       self.photo_thumb_size)

        context = self.context
        request = self.request
        api = self.api

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



        self.profile = profile_details
        self.communities = communities
        self.my_communities = my_communities or []
        self.preferred_communities = preferred_communities
        self.tags = tags
        self.actions = get_profile_actions(context,request)
        self.head_data = convert_to_script(client_json_data)
        return self.make_response()

    def prepare_response(self):
        """ Prepare all the data needed by a template without actually rendering
        anything so that subclasses can add additional information as they see fit.
        """
        self.response = {'api':self.api,
            'profile_currently_viewed':self.profile,
            'actions':self.actions,
            'head_data':self.head_data,
            'communities':self.communities,
            'my_communities':self.my_communities,
            'preferred_communities':self.preferred_communities,
            'tags':self.tags,
            'recent_items':[],
            'feed_url':model_url(self.context, self.request, "atom.xml"),
            'comments':comments_to_display(self.request),
            }

    def make_response(self):
        response = self.prepare_response()
        return render_template_to_response('templates/profile.pt', **self.response)


@bfg_view(for_=IProfile, name="thumbnail")
def profile_thumbnail(context, request):
    api = request.api
    api.page_title = 'Profile thumbnail redirector'
    photo = context.get('photo')
    if photo is not None:
        url = thumb_url(photo, request, PROFILE_THUMB_SIZE)
    else:
        url = api.static_url + "/img/default_user.png"
    return HTTPFound(location=url)

class EditProfileFormController(ContentController):

    class Schema(MappingSchema):

        first_name = SchemaNode(
            String(),
            )
        last_name = SchemaNode(
            String(),
            )
        email = SchemaNode(
            String(),
            validator=Email(),
            title='Email address',
            )
        password = SchemaNode(
            String(),
            widget=CheckedPasswordWidget(),
            title='Change Password',
            missing=''
            )
        photo = SchemaNode(
            FileData(),
            widget=AvatarWidget(),
            title='Profile image',
            missing=None,
            validator=Function(is_image),
            )

        @instantiate()
        class details(MappingSchema):

            position = SchemaNode(
                String(),
                missing='',
                )
            organisation = SchemaNode(
                String(),
                missing='',
                )
            biography = SchemaNode(
                String(),
                widget=TextAreaWidget(),
                title='Short bio',
                missing='',
                description='Summarize your story in one or two sentences.'
                )

            @instantiate(missing=())
            class websites(SequenceSchema):
                url = SchemaNode(
                    String(),
                    title='website',
                    validator=Function(valid_url)
                    )

            country = SchemaNode(
                String(),
                widget=SelectWidget(
                    values=[('', 'Select your country')] + countries,
                    description='Where do you currently live?'
                    )
                )

            @instantiate()
            class social_networks(MappingSchema):

                twitter = SchemaNode(
                    String(),
                    title='Twitter Username',
                    missing='',
                    validator=Regex('^@[a-zA-Z_]+',
                                    'This is not a valid twitter username')
                    )
                facebook = SchemaNode(
                    String(),
                    title='Facebook page',
                    missing=''
                    )

    def __init__(self, context, request):
        super(EditProfileFormController,self).__init__(context,request,form_template='_form_profile_edit')
        self.social_category = social_category(context, None)
        if not self.social_category:
            # the social category is lazily instantiated
            self.social_category = context.categories['social'] = SocialCategory()

    def form_defaults(self):
         context = self.context
         assert(context.websites != None)
         defaults = dict(
             first_name=context.firstname,
             last_name=context.lastname,
             email=context.email,
             details=dict(
                 position=context.position,
                 organization=context.organization,
                 biography=context.biography,
                 country=context.country,
                 websites=context.websites,
                 social_networks=dict(),
                 )
             )
         socials = defaults['details']['social_networks']
         for name in ('facebook','twitter'):
             item = self.social_category.get(name)
             if item is not None:
                 socials[name]=item.id
         return defaults

    def handle_content(self, context, request, validated):
        # Handle the easy ones
        context.firstname=validated['first_name']
        context.lastname=validated['last_name']
        context.email=validated['email']
        context.position=validated['details']['position']
        context.organisation=validated['details']['organisation']
        context.biography=validated['details']['biography']
        context.country=validated['details']['country']

        # change password
        users = find_users(context)
        if validated['password']:
            users = find_users(context)
            users.change_password(context.__name__,validated['password'])

        # handle websites
        context.websites=[]
        for url in validated['details']['websites']:
            if not (
                url.startswith('http://') or
                url.startswith('https://')
                ):
                url = 'http://'+url
            context.websites.append(url)

        # Handle the picture
        handle_photo_upload(context, request, validated['photo'])

        # Handle the social networking stuff
        socials = validated['details']['social_networks']
        for name in ('facebook', 'twitter'):
            id = socials[name]
            if id:
                item = self.social_category.get(name)
                if not item:
                    item = SocialCategoryItem(
                        id=id, title=name, description=u''
                        )
                    context.categories['social'][name] = item
                else:
                    item.id = id

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
    api = request.api
    api.page_title = page_title
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
    api = request.api
    api.page_title = page_title

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
    api = request.api
    api.page_title = page_title

    # Show confirmation page.
    return dict(api=api)

class ResetConfirmController(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.api = TemplateAPI(self.context, self.request, 'Reset Password')

    def __call__(self):
        key = self.request.params.get('key')
        if not key or len(key) != 40:
            self.api.page_title = 'Password Reset URL Problem'
            return render_template_to_response('templates/reset_failed.pt',
                                               api=api)


        if self.request.method == 'POST':
            # todo: validate and convert
            return self.handle_submit(self.api.formdata)

        return self.make_response()

    def make_response(self):
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
                # XXX should be part of form validation
                raise Exception(login='No such user account exists')
            userid = user.get('id')
            if userid is None:
                userid = user['login']

            profiles = find_profiles(context)
            profile = profiles.get(userid)
            if profile is None:
                # XXX should be part of form validation
                raise Exception(login='No such profile exists')

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
            api = request.api
            api.page_title = page_title
            return render_template_to_response(
                'templates/reset_complete.pt',
                api=api,
                login=converted['login'],
                password=converted['password'],
                )

        except ResetFailed, e:
            api = request.api
            api.page_title = e.page_title
            return render_template_to_response('templates/reset_failed.pt',
                                               api=api)

class ResetFailed(Exception):
    pass

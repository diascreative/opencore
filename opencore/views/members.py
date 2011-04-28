"""Community membership views, both for browsing and managing.

Includes invitations, per-user preferences on alerts, etc.
"""
import transaction

from email.Message import Message
from webob import Response
from simplejson import JSONEncoder
import logging

from webob.exc import HTTPFound
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.index.text.parsetree import ParseError

from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.security import has_permission
from repoze.bfg.security import effective_principals
from repoze.bfg.traversal import model_path
from repoze.bfg.traversal import find_interface
from repoze.bfg.url import model_url
from repoze.bfg.exceptions import ExceptionResponse

from formencode import Invalid as FormEncodeInvalid

from repoze.lemonade.content import create_content
from repoze.sendmail.interfaces import IMailDelivery

from opencore.views.api import TemplateAPI
from opencore.views.batch import get_catalog_batch

from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import IProfile
from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IInvitation
from opencore.security.policy import to_profile_active 
from opencore.utilities.image import thumb_url
from opencore.utilities.interfaces import IRandomId

from opencore.utils import find_profiles
from opencore.utils import find_users
from opencore.utils import find_site
from opencore.utils import get_setting
from opencore.consts import countries

from opencore.views.interfaces import IInvitationBoilerplate
from opencore.views.utils import handle_photo_upload
from opencore.views.utils import photo_from_filestore_view
from opencore.views.validation import InviteMemberSchema
from opencore.views.validation import SignupMemberSchema
from opencore.views.validation import AcceptInvitationSchema
from opencore.views.validation import ValidationError
from opencore.views.validation import UnicodeString
from opencore.views.validation import StringBool
from opencore.views.validation import State


log = logging.getLogger(__name__)
PROFILE_THUMB_SIZE = (75, 100)

def _get_manage_actions(community, request):

    # Filter the actions based on permission in the **community**
    actions = []
    if has_permission('moderate', community, request):
        actions.append(('Manage Members', 'manage.html'))
        actions.append(('Add', 'invite_new.html'))

    return actions

def _get_common_email_info(community, community_href):
    info = {}
    info['system_name'] = get_setting(community, 'system_name', 'OpenCore')
    info['system_email_domain'] = get_setting(community,
                                              'system_email_domain')
    info['from_name'] = '%s invitation' % info['system_name']
    info['from_email'] = 'invitation@%s' % info['system_email_domain']
    info['c_title'] = community.title
    info['c_description'] = community.description
    info['c_href'] = community_href
    info['mfrom'] = '%s <%s>' % (info['from_name'], info['from_email'])

    return info

def _member_profile_batch(context, request):
    community = find_interface(context, ICommunity)
    member_names = community.member_names
    profiles_path = model_path(find_profiles(context))
    batch = get_catalog_batch(
        context, request,
        batch_size = 12,
        interfaces = [IProfile],
        path={'query': profiles_path, 'depth': 1},
        allowed={'query': effective_principals(request), 'operator': 'or'},
        name = list(member_names),
        sort_index='lastfirst',
        )
    return batch

def show_members_view(context, request):
    """Default view of community members (with/without pictures)."""

    page_title = 'Community Members'
    api = request.api
    api.page_title = page_title

    # Filter the actions based on permission in the **community**
    community = find_interface(context, ICommunity)
    actions = _get_manage_actions(community, request)

    # Did we get the "show pictures" flag?
    hp = request.params.has_key('hide_pictures')
    mu = model_url(context, request)
    submenu = [
        {'label': 'Show Pictures',
         'href': mu, 'make_link': hp},
        {'label': 'Hide Pictures',
         'href': mu + '?hide_pictures', 'make_link': not(hp)},
        ]

    profiles = find_profiles(context)
    member_batch = _member_profile_batch(context, request)
    member_entries = member_batch['entries']
    moderator_names = community.moderator_names

    member_info = []
    for i in range(len(member_entries)):
        derived = {}
        entry = member_entries[i]
        derived['title'] = entry.title
        derived['href'] = model_url(entry, request)
        derived['position'] = entry.position
        derived['organization'] = entry.organization
        derived['phone'] = entry.phone
        derived['department'] = entry.department
        derived['email'] = entry.email
        derived['city'] = entry.location

        photo = entry.get('photo')
        if photo is not None:
            derived['photo_url'] = thumb_url(photo, request,
                                             PROFILE_THUMB_SIZE)
        else:
            derived['photo_url'] = api.static_url + "/images/defaultUser.gif"

        derived['is_moderator'] = entry.__name__ in moderator_names
        # Chameleon's tal:repeat and repeat variable support for
        # things like index is pretty iffy.  Fix the entry info to
        # supply the CSS class information.
        derived['css_class'] = 'photoProfile'
        if derived['is_moderator']:
            derived['css_class'] += ' moderator'
        member_info.append(derived)

    moderator_info = []
    profiles = find_profiles(context)
    for moderator_name in moderator_names:
        if moderator_name in profiles:
            derived = {}
            profile = profiles[moderator_name]
            if not has_permission('view', profile, request):
                continue
            derived['title'] = profile.title
            derived['href'] = model_url(profile, request)
            moderator_info.append(derived)

    return render_template_to_response(
        'templates/show_members.pt',
        api=api,
        actions=actions,
        submenu=submenu,
        moderators=moderator_info,
        members=member_info,
        batch_info=member_batch,
        hide_pictures=hp,
        )


def _send_moderators_changed_email(community,
                                   community_href,
                                   new_moderators,
                                   old_moderators,
                                   cur_moderators,
                                   prev_moderators):
    info = _get_common_email_info(community, community_href)
    subject_fmt = 'Change in moderators for %s'
    subject = subject_fmt % info['c_title']
    body_template = get_template('templates/email_moderators_changed.pt')

    profiles = find_profiles(community)
    all_moderators = cur_moderators | prev_moderators
    to_profiles = [profiles[name] for name in all_moderators]
    to_addrs = ["%s <%s>" % (p.title, p.email) for p in to_profiles]

    mailer = getUtility(IMailDelivery)
    msg = Message()
    msg['From'] = info['mfrom']
    msg['To'] = ",".join(to_addrs)
    msg['Subject'] = subject
    body = body_template(
        system_name=info['system_name'],
        community_href=info['c_href'],
        community_name=info['c_title'],
        new_moderators=[profiles[name].title for name in new_moderators],
        old_moderators=[profiles[name].title for name in old_moderators],
        cur_moderators=[profiles[name].title for name in cur_moderators],
        prev_moderators=[profiles[name].title for name in prev_moderators]
        )

    if isinstance(body, unicode):
        body = body.encode("UTF-8")

    msg.set_payload(body, "UTF-8")
    msg.set_type('text/html')
    mailer.send(info['mfrom'], to_addrs, msg)

class ManageMembersController(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.community = find_interface(context, ICommunity)
        self.profiles = find_profiles(self.community)
        self.api = request.api
        self.actions = _get_manage_actions(self.community, request)
        self.desc = ('Use the form below to remove members or to resend invites '
                'to people who have not accepted your invitation to join '
                'this community.')
        self.defaults = self.form_defaults()

    def _getInvitations(self):
        L = []
        for invitation in self.context.values():
            if IInvitation.providedBy(invitation):
                L.append(invitation)
        return L

    def form_defaults(self):
        records = []
        community = self.community
        profiles = self.profiles
        member_names = community.member_names
        moderator_names = community.moderator_names
        for mod_name in moderator_names:
            profile = profiles[mod_name]
            sortkey = (0, '%s, %s' % (profile.lastname, profile.firstname))
            record = {
                'sortkey':sortkey,
                'name':mod_name,
                'title':profile.title,
                'moderator':True,
                'member':True,
                'resend':False,
                'remove':False,
                'invite':False,
                }
            records.append(record)
        for mem_name in member_names:
            if mem_name in moderator_names:
                continue
            profile = profiles[mem_name]
            sortkey = (1, '%s, %s' % (profile.lastname, profile.firstname))
            record = {
                'sortkey':sortkey,
                'name':mem_name,
                'title':profile.title,
                'member':True,
                'moderator':False,
                'resend':False,
                'remove':False,
                'invite':False,
                }
            records.append(record)
        for invitation in self._getInvitations():
            sortkey = (2, invitation.email)
            record = {
                'sortkey':sortkey,
                'title':invitation.email,
                'name':invitation.__name__,
                'member':False,
                'moderator':False,
                'resend':False,
                'remove':False,
                'invite':True,
                }
            records.append(record)
        records.sort(key=lambda x: x['sortkey'])
        return {'members':records}

    def __call__(self):
        community = self.community
        context = self.context
        request = self.request
       
        if self.request.method == 'POST':
            # create a dict of the members list key'd on name
            converted = dict(map(lambda x: (x['name'], x), self.defaults['members']))
            form_keys = ['moderator', 'resend', 'remove']
            
            for k, v in self.request.POST.iteritems():
                if k == 'submit' : continue
                action, name = k.split('_')
                if action not in form_keys: continue
                converted[name][action] = v=='True'
                
            return self.handle_submit(converted.values())
            
        return self.make_response()
    
     
    def make_response(self):
        error = self.api.formerrors.get('members', None)
        if error:
            log.debug('error=%s' % str(error))
            self.api.error_message = 'Please correct the indicated errors.'
        return render_template_to_response(
                       'templates/members_manage.pt',
                       api=self.api,
                       actions=self.actions,
                       page_title='Manage Community Members',
                       page_description=self.desc,
                       defaults=self.defaults,
                       error=error)  
        
    def handle_submit(self, converted):
        log.debug('ManageMembersController.handle_submit converted: %s' % str(converted))
        results = []
        community = self.community
        community_href = model_url(community, self.request)
        context = self.context
        request = self.request
        moderators = community.moderator_names # property
        members = community.member_names # property
        invitation_names = [ x.__name__ for x in self._getInvitations() ]
     
        members_group_name = community.members_group_name
        moderators_group_name = community.moderators_group_name

        users = find_users(context)

        results = []

        for record in converted:
            name = record['name']
            if record['remove']:
                if name in members:
                    users.remove_group(name, members_group_name)
                    results.append('Removed member %s' % record['title'])
                if name in moderators:
                    users.remove_group(name, moderators_group_name)
                    results.append('Removed moderator %s' %
                                   record['title'])
                if name in invitation_names:
                    del context[name]
                    results.append('Removed invitation %s' %
                                   record['title'])
            else:
                if record['resend']:
                    invitation = context.get(name)
                    _send_invitation_email(request, community, community_href,
                                           invitation)
                    results.append('Resent invitation to %s'%
                                   record['title'])
                else:
                    if (name in moderators) and (not record['moderator']):
                        users.remove_group(name, moderators_group_name)
                        results.append('%s is no longer a moderator'%
                                       record['title'])
                    if (not name in moderators) and record['moderator']:
                        users.add_group(name, moderators_group_name)
                        results.append('%s is now a moderator' %
                                       record['title'])

        # Invariant: Don't allow removal of the last moderator.
        if not community.moderator_names:
            transaction.abort()
            raise ValidationError(self,
                members="Must leave at least one moderator for community.")

        cur_moderators = community.moderator_names
        new_moderators = cur_moderators - moderators
        old_moderators = moderators - cur_moderators
        if new_moderators or old_moderators:
            _send_moderators_changed_email(community, community_href,
                                           new_moderators, old_moderators,
                                           cur_moderators, moderators)
        joined_result = ', '.join(results)
        status_message = 'Membership information changed: %s' % joined_result
        location = model_url(context, request, "manage.html",
                             query={"status_message": status_message})
        return HTTPFound(location=location)


def _send_aeu_emails(community, community_href, profiles, text):
    # To make reading the add_existing_user_view easier, move the mail
    # delivery part here.

    info = _get_common_email_info(community, community_href)
    subject_fmt = 'You have been added to the %s community'
    subject = subject_fmt % info['c_title']
    body_template = get_template('templates/email_add_existing.pt')
    html_body = text

    mailer = getUtility(IMailDelivery)
    for profile in profiles:
        to_email = profile.email

        msg = Message()
        msg['From'] = info['mfrom']
        msg['To'] = to_email
        msg['Subject'] = subject
        body = body_template(
            system_name=info['system_name'],
            community_href=info['c_href'],
            community_name=info['c_title'],
            community_description=info['c_description'],
            personal_message=html_body,
            )

        if isinstance(body, unicode):
            body = body.encode("UTF-8")

        msg.set_payload(body, "UTF-8")
        msg.set_type('text/html')
        mailer.send(info['mfrom'], [to_email,], msg)



def _add_existing_users(context, community, profiles, text, request, status=None):
    users = find_users(community)
    for profile in profiles:
        group_name = community.members_group_name
        user_name = profile.__name__
        users.add_group(user_name, group_name)

    # Generate HTML and text mail messages and send a mail for
    # each user added to the community.
    community_href = model_url(community, request)
    _send_aeu_emails(community, community_href, profiles, text)

    # We delivered invitation messages to each user.  Redirect to
    # Manage Members with a status message.
    n = len(profiles)
    if n == 1:
        msg = 'One member added and email sent.'
    else:
        fmt = '%s members added and emails sent.'
        msg = fmt % len(profiles)
    if status:
        msg = msg + ' ' + status    
    location = model_url(context, request, 'manage.html',
                         query={'status_message': msg})
    return HTTPFound(location=location)


class AcceptInvitationController(object):
    '''
    Handles email invitation links for site signup and new project members.
    signup & members are both folders with invitations.
    i.e. http://127.0.0.1:6544/signup/hifebi &
         http://127.0.0.1:6544/projects/x/members/ywryw
         
    todo: use IInvitationBoilerplate for t&c.     
    '''
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.community = find_interface(context, ICommunity)
        self.profiles = find_profiles(context)
        self.api = request.api

    def __call__(self):
        context = self.context
        request = self.request
        
        self.system_name = get_setting(context, 'system_name', 'OpenCore')
        if self.community:
            community_name = self.community.title
            self.desc = ('You have been invited to join the "%s" in %s.  Please begin '
                'by creating a %s login with profile information.' %
                (community_name, self.system_name, self.system_name))
        
        else:
            self.desc = ('You have been invited to join the "%s".  Please begin '
                'by creating a %s login with profile information.' %
                (self.system_name, self.system_name))
       
        if request.method == 'POST':
            post_data = request.POST
            try:
                validation_info = State(users=set(self.profiles.keys()))
                self.api.formdata = AcceptInvitationSchema.to_python(post_data, state=validation_info)
            except FormEncodeInvalid, e:
                self.api.formdata = post_data
                raise ValidationError(self, **e.error_dict)
            else:
                return self.handle_submit(self.api.formdata)
    
        return self.make_response()
         
    def make_response(self):
        return render_template_to_response(
              'templates/accept_invitation.pt',
              api=self.api,
              page_title='Accept %s Invitation' % self.system_name,
              page_description=self.desc,
              countries=[('', 'Select your Country')] + countries
            )
  
    def handle_submit(self, converted):
        context = self.context
        community = self.community
        request = self.request
        users = find_users(context)
        profiles = self.profiles

        password = converted['password']
        password_confirm = converted['password_confirm']
        username = converted['username']

        if community:
            community_href = model_url(community, request)
            groups = [ community.members_group_name ]
            users.add(username, username, password, groups)
        
        plugin = request.environ['repoze.who.plugins']['auth_tkt']
        identity = {'repoze.who.userid':username}
        remember_headers = plugin.remember(request.environ, identity)
        profile = create_content(
            IProfile,
            firstname=converted['firstname'],
            lastname=converted['lastname'],
            email=context.email,
            country=converted['country'],
            dob=converted['dob'],
            gender=converted['gender']
            )
        profiles[username] = profile
        to_profile_active(profile)
            
        del context.__parent__[context.__name__]
        
        if community:
            url = model_url(community, request,
                        query={'status_message':'Welcome!'})
            _send_ai_email(community, community_href, username, profile)
        else:
            url = request.api.app_url+'?status_message=Welcome!'
            _send_signup_ai_email(request, username, profile)
                
        return HTTPFound(headers=remember_headers, location=url)

def _send_ai_email(community, community_href, username, profile):
    """Send email to user who has accepted a community invitation.
    """
    info = _get_common_email_info(community, community_href)
    subject_fmt = 'Thank you for joining the %s community'
    subject = subject_fmt % info['c_title']
    body_template = get_template('templates/email_accept_invitation.pt')

    mailer = getUtility(IMailDelivery)
    msg = Message()
    msg['From'] = info['mfrom']
    msg['To'] = profile.email
    msg['Subject'] = subject
    body = body_template(
        community_href=info['c_href'],
        community_name=info['c_title'],
        community_description=info['c_description'],
        username=username,
        )

    if isinstance(body, unicode):
        body = body.encode("UTF-8")

    msg.set_payload(body, "UTF-8")
    msg.set_type('text/html')
    mailer.send(info['mfrom'], [profile.email,], msg)
    
def _send_signup_ai_email(request, username, profile):
    """Send email to user who has signed up to site.
    """
    info = {}
    info['system_name'] = get_setting(profile, 'system_name', 'OpenCore')
    info['system_email_domain'] = get_setting(profile, 'system_email_domain')
    info['from_name'] = '%s invitation' % info['system_name']
    info['from_email'] = 'invitation@%s' % info['system_email_domain']
    info['c_title'] = info['system_name']
    info['c_description'] = ""
    info['c_href'] = request.api.app_url
    info['mfrom'] = '%s <%s>' % (info['from_name'], info['from_email'])
    info['subject'] = 'Thank you for joining the %s community' % info['system_name']
  
    body_template = get_template('templates/email_accept_signup_invitation.pt')

    mailer = getUtility(IMailDelivery)
    msg = Message()
    msg['From'] = info['mfrom']
    msg['To'] = profile.email
    msg['Subject'] = info['subject'] 
    body = body_template(
        system_name=info['system_name'],
        system_href=info['c_href'],                 
        username=username,
        )

    if isinstance(body, unicode):
        body = body.encode("UTF-8")

    msg.set_payload(body, "UTF-8")
    msg.set_type('text/html')
    mailer.send(info['mfrom'], [profile.email,], msg)    
    

class InviteNewUsersController(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.community = find_interface(context, ICommunity)
        self.api = request.api
        self.actions = _get_manage_actions(self.community, request)
        self.profiles = find_profiles(context)
        self.desc = ('Type the first few letters of the name of the person you '
                'would like to add to this community, select their name, '
                'and press submit. Alternatively type in email addresses each on a separate line for new members. The short message below is included '
                'along with the text of your invite.')
        self.system_name = get_setting(context, 'system_name', 'OpenCore')
  
    def __call__(self):
        community = self.community
        context = self.context
        request = self.request
       
        if self.request.method == 'POST':
            post_data = self.request.POST
            log.debug('request.POST: %s' % post_data)
            log.debug('api.formdata: %s' % self.api.formdata)
            try:
                # validate and convert
                validation_info = State(users=set(self.profiles.keys())) 
                self.api.formdata = InviteMemberSchema().to_python(post_data, state=validation_info)
            except FormEncodeInvalid, e:
                self.api.formdata = post_data
                raise ValidationError(self, **e.error_dict)
            else:
                return self.handle_submit(self.api.formdata, validation_info)
        else:
            # Handle userid passed in via GET request
            # Moderator would get here by clicking a link in an email to grant a
            # user's request to join this community.
            add_user_id = request.params.get("user_id", None)
            if add_user_id is not None:
                profile = self.profiles.get(add_user_id, None)
                if profile is not None:
                    return _add_existing_users(context, community, [profile,],
                                               "", request)    
            
        return self.make_response()
    
    def make_response(self):
        return render_template_to_response(
                       'templates/members_invite_new.pt',
                       api=self.api,
                       actions=self.actions,
                       page_title='Invite New %s Users' % self.system_name,
                       page_description=self.desc)     
   
    def handle_submit(self, converted, validation_info):
        log.debug('InviteNewUsersController.handle_submit: %s, %s' % (str(converted), str(validation_info)))
        request = self.request
        context = self.context
        community = self.community
        profiles = self.profiles
        
        email_addresses = converted['email_addresses']
        usernames = converted['users']
        
        if not email_addresses and not usernames:
            raise ValidationError(self, email_addresses='you must supply either an email address or pick a user.')
        
        status = ''
        if email_addresses:
            status = self.handle_email_submit(converted)
        
       
        if not usernames:
            location = model_url(context, request, 'manage.html',
                             query={'status_message': status})
            return HTTPFound(location=location)
                
        if validation_info.user_type == 'user':
            usernames = [usernames]
        
        users = []        
        for username in usernames:
            users.append(self.profiles[username])
        return _add_existing_users(self.context, self.community, users,
                                   converted['text'], self.request, status)



    def handle_email_submit(self, converted):
        log.debug('InviteNewUsersController.handle_email_submit: %s' % str(converted))
        context = self.context
        request = self.request
        community = self.community
        random_id = getUtility(IRandomId)
        members = community.member_names | community.moderator_names
        community_href = model_url(community, request)

        search = ICatalogSearch(context)

        addresses = converted['email_addresses']
        html_body = converted['text']

        ninvited = nadded = nignored = 0

        for email_address in addresses:
            # Check for existing members
            total, docids, resolver = search(email=email_address.lower(),
                                             interfaces=[IProfile,])

            if total:
                # User is already in the system
                profile = resolver(docids[0])
            
                if profile.__name__ in members:
                    # User is a member of this community, do nothing
                    nignored += 1

                else:
                    # User is in the system but not in this community.  If user is
                    # active, just add them to the community as though we had
                    # used the add existing user form.
                    if profile.security_state == 'active':
                        _add_existing_users(context, community, [profile,],
                                            html_body, request)
                        nadded += 1
                    else:
                        msg = ('Address, %s, belongs to a user which has '
                               'previously been deactivated.  This user must '
                               'be reactivated by a system administrator '
                               'before they can be added to this community.' %
                               email_address)
                        raise ValidationError(self, email_addresses=msg)

            else:
                # Invite new user 
                invitation = create_content(
                    IInvitation,
                    email_address,
                    html_body
                )
                while 1:
                    name = random_id()
                    if name not in context:
                        context[name] = invitation
                        break

                _send_invitation_email(request, community, community_href,
                                       invitation)
                ninvited += 1

        status = ''

        if ninvited:
            if ninvited == 1:
                status = 'One user invited.  '
            else:
                status = '%d users invited.  ' % ninvited

        if nadded:
            if nadded == 1:
                status += 'One existing user added to community.  '
            else:
                status += ('%d existing users added to community.  '
                           % nadded)
        if nignored:
            if nignored == 1:
                status += 'One user already member.'
            else:
                status += '%d users already members.' % nignored
        
        return status 


      
def _send_invitation_email(request, community, community_href, invitation):
    mailer = getUtility(IMailDelivery)
    info = _get_common_email_info(community, community_href)
    subject_fmt = 'Please join the %s community at %s'
    info['subject'] = subject_fmt % (info['c_title'],
                                     info['system_name'])
    body_template = get_template('templates/email_invite_new.pt')

    msg = Message()
    msg['From'] = info['mfrom']
    msg['To'] = invitation.email
    msg['Subject'] = info['subject']
    body = body_template(
        system_name=info['system_name'],
        community_href=info['c_href'],
        community_name=info['c_title'],
        community_description=info['c_description'],
        personal_message=invitation.message,
        invitation_url=model_url(invitation.__parent__, request,
                                 invitation.__name__)
        )

    if isinstance(body, unicode):
        body = body.encode("UTF-8")

    msg.set_payload(body, "UTF-8")
    msg.set_type('text/html')
    mailer.send(info['mfrom'], [invitation.email,], msg)
    
def _send_signup_email(request, invitation):
    site = find_site(request.context)
    mailer = getUtility(IMailDelivery)
    
    info = {}
    info['system_name'] = get_setting(site, 'system_name', 'OpenCore')
    info['system_email_domain'] = get_setting(site, 'system_email_domain')
    info['from_name'] = '%s invitation' % info['system_name']
    info['from_email'] = 'invitation@%s' % info['system_email_domain']
    info['c_title'] = info['system_name']
    info['c_description'] = ""
    info['c_href'] = model_url(site, request)
    info['mfrom'] = '%s <%s>' % (info['from_name'], info['from_email'])
    info['subject'] = 'Please join the %s community' % info['system_name']
    
    body_template = get_template('templates/email_signup.pt')

    msg = Message()
    msg['From'] = info['mfrom']
    msg['To'] = invitation.email
    msg['Subject'] = info['subject']
    body = body_template(
        system_name=info['system_name'],
        personal_message=invitation.message,
        invitation_url=model_url(site, request, 'signup', invitation.__name__)
        )

    if isinstance(body, unicode):
        body = body.encode("UTF-8")

    msg.set_payload(body, "UTF-8")
    msg.set_type('text/html')
    mailer.send(info['mfrom'], [invitation.email,], msg)    

def jquery_member_search_view(context, request):
    prefix = request.params['val'].lower()
    community = find_interface(context, ICommunity)
    member_names = community.member_names
    moderator_names = community.moderator_names
    community_member_names = member_names.union(moderator_names)
    query = dict(
        member_name='%s*' % prefix,
        sort_index='title',
        limit=20,
        )
    searcher = ICatalogSearch(context)
    try:
        total, docids, resolver = searcher(**query)
        profiles = filter(None, map(resolver, docids))
        records = [dict(
                    id = profile.__name__,
                    text = profile.title,
                    )
                   for profile in profiles
                   if profile.__name__ not in community_member_names
                   and profile.security_state != 'inactive']
    except ParseError:
        records = []
    result = JSONEncoder().encode(records)
    return Response(result, content_type="application/x-json")

class JoinNewUsersController(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.community = find_interface(context, ICommunity)
        self.api = request.api
        self.api.page_title = 'Signup'
        self.profiles = find_profiles(context)
        self.desc = ('Type in you email address and you will be sent a signup email shortly.')
        self.system_name = get_setting(context, 'system_name', 'OpenCore')
  
    def __call__(self):
        community = self.community
        context = self.context
        request = self.request
       
        if self.request.method == 'POST':
            post_data = self.request.POST
            log.debug('request.POST: %s' % post_data)
            try:
                # validate and convert
                self.api.formdata = SignupMemberSchema().to_python(post_data)
            except FormEncodeInvalid, e:
                self.api.formdata = post_data
                raise ValidationError(self, **e.error_dict)
            else:
                return self.handle_submit(self.api.formdata)
       
            
        return self.make_response()
    
    def handle_submit(self, converted):
        context = self.context
        request = self.request
        random_id = getUtility(IRandomId)
       
        search = ICatalogSearch(context)

        email_address = converted['email_address']
     
        # Check for existing member
        total, docids, resolver = search(email=email_address.lower(),
                                             interfaces=[IProfile,])
        if total:
            # User is already in the system
            profile = resolver(docids[0])
            if profile.security_state == 'inactive':
                msg = ('Address, %s, belongs to a user which has '
                               'previously been deactivated.  This user must '
                               'be reactivated by a system administrator '
                               'before they can join up.' %  email_address)
                raise ValidationError(email_address=msg)
            # User is a member of this community, do nothing
            status = 'You are already a member.'

        else:
            # Invite new user 
            invitation = create_content(
                IInvitation,
                email_address,
                "We look forward to you joining."
            )
            while 1:
                name = random_id()
                if name not in context:
                    context[name] = invitation
                    break
            _send_signup_email(request, invitation)
            status = 'You have been sent a signup email.'
     
        return HTTPFound(location='/?status_message=%s' % status)      
     
    
    def make_response(self):
        return render_template_to_response(
                       'templates/members_signup.pt',
                       api=self.api,
                       actions=(),
                       page_title='Welcome to %s' % self.system_name,
                       page_description=self.desc)     

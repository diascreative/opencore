# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz@sorosny.org
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Community membership views, both for browsing and managing.

Includes invitations, per-user preferences on alerts, etc.
"""
import transaction

from colander import (
    All,
    Boolean,
    Date,
    Email,
    Function,
    Invalid,
    MappingSchema,
    Regex,
    SchemaNode,
    SequenceSchema,
    String,
    null,
    )
from deform.widget import (
    CheckedPasswordWidget,
    DatePartsWidget,
    SelectWidget,
    TextAreaWidget,
    TextInputWidget,
    HiddenWidget,
    )

from email.Message import Message
from webob import Response
from simplejson import JSONEncoder
import logging

from webob.exc import HTTPFound
from zope.component import getUtility
from zope.index.text.parsetree import ParseError

from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.security import has_permission
from repoze.bfg.security import effective_principals
from repoze.bfg.traversal import model_path
from repoze.bfg.traversal import find_interface
from repoze.bfg.url import model_url

from repoze.lemonade.content import create_content
from repoze.sendmail.interfaces import IMailDelivery

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

from opencore.views.forms import (
    _get_manage_actions,
    BaseController,
    KarlUserWidget,
    CommaSeparatedList,
    TOUWidget,
    instantiate,
    )
from opencore.views.validation import ValidationError


log = logging.getLogger(__name__)
PROFILE_THUMB_SIZE = (75, 100)

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
            derived['photo_url'] = api.static_url + "/img/default_user.png"

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


class MembersBaseController(BaseController):

    def __init__(self, *args):
        super(MembersBaseController,self).__init__(*args)
        self.community = find_interface(self.context, ICommunity)
        self.actions = _get_manage_actions(self.community, self.request)
        self.profiles = find_profiles(self.context)
        self.system_name = get_setting(
            self.context, 'system_name', 'OpenCore'
            )
        self.data['actions']=self.actions

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


class AcceptInvitationController(MembersBaseController):
    '''
    Handles email invitation links for site signup and new project members.
    signup & members are both folders with invitations.
    i.e. http://127.0.0.1:6544/signup/hifebi &
         http://127.0.0.1:6544/projects/x/members/ywryw
    '''

    # schema
    
    class _Schema(MappingSchema):

        username = SchemaNode(
            String(),
            )
        password = SchemaNode(
            String(),
            widget=CheckedPasswordWidget()
            )
        first_name = SchemaNode(
            String(),
            )
        last_name = SchemaNode(
            String(),
            )
        country = SchemaNode(
            String(),
            widget=SelectWidget(
                values=[('', 'Select your country')] + countries
                )
            )
        date_of_birth = SchemaNode(
            Date(),
            widget=DatePartsWidget(),
            missing=None,
            )
        gender = SchemaNode(
            String(),
            widget=SelectWidget(
                values=[('', 'Select your gender'),
                        ('male', 'male'),
                        ('female', 'female'),]
                ),
            missing=''
            )
        terms_of_use = SchemaNode(
            Boolean(),
            widget=TOUWidget(),
            validator=Function(
                lambda value: value==True,
                'You must agree to the terms of use',
                )
            )

    # buttons
        
    buttons = ('join up',)
    
    # form-specific validators
        
    def not_a_profile(self,value):
        if value in self.profiles:
            return False
        return True
    
    # schema instantiation
    
    def Schema(self):
        # This needs to be a function some validators needs context
        s = self._Schema().clone()
        s['username'].validator=All(
            Regex(
                '^[\w-]+$',
                'Username must contain only letters, numbers, and dashes'
                ),
            Function(
                self.not_a_profile,
                'This username is already taken'
                ),
            )
        return s
    
    def handle_submit(self, validated):
        context = self.context
        community = self.community
        request = self.request
        users = find_users(context)
        profiles = self.profiles

        password = validated['password']
        username = validated['username']

        if community:
            community_href = model_url(community, request)
            groups = [ community.members_group_name ]
            users.add(username, username, password, groups)
        else:
            users.add(username, username, password)
                    
        plugin = request.environ['repoze.who.plugins']['auth_tkt']
        identity = {'repoze.who.userid':username}
        remember_headers = plugin.remember(request.environ, identity)
        profile = create_content(
            IProfile,
            firstname=validated['first_name'],
            lastname=validated['last_name'],
            email=context.email,
            country=validated['country'],
            dob=validated['date_of_birth'],
            gender=validated['gender']
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
    

class NewUsersBaseController(MembersBaseController):

    def __init__(self,*args):
        super(NewUsersBaseController,self).__init__(*args)
        # storage for members found during validation
        # address -> profile
        self.emails_existing = {}
        
    # form-specific validators
        
    def not_deactivated(self,value):
        search = ICatalogSearch(self.context)
        total, docids, resolver = search(email=value.lower(),
                                             interfaces=[IProfile,])
        if total:
            profile = resolver(docids[0])
            if profile.security_state == 'active':
                self.emails_existing[value.lower()]=profile
            else:
                return False
        return True

    # schema instantiation

    def email_validator(self):
        return All(
            Email(),
            Function(self.not_deactivated,
                     'This address belongs to a user which has '
                     'previously been deactivated.  This user must '
                     'be reactivated by a system administrator '
                     'before they can be added to this community.')
            )

    def email_list_validator(self):
        def validator(node, value):
            for item in value:
                validate_email = self.email_validator()
                validate_email(node, item)
        return validator

class InviteNewUsersController(NewUsersBaseController):

    buttons = ('cancel', 'send')

    # schema
    
    class _Schema(MappingSchema):
        
        @instantiate(widget=KarlUserWidget(),missing=())
        class users(SequenceSchema):
            user = SchemaNode(
                String(),
                )

        email_addresses = SchemaNode(
                CommaSeparatedList(),
                widget=TextInputWidget(),
                missing=[]
                )

        text = SchemaNode(
            String(),
            widget=TextAreaWidget(),
            missing='',
            )

        return_to = SchemaNode(
                String(),
                widget=HiddenWidget(),
                missing = None,
                )

    # form-specific validators
        
    def valid_profile(self,value):
        if value in self.profiles:
            return True
    
    def users_or_emails(self,form,value):
        if not (value['email_addresses'] or value['users']):
            message = 'you must supply either an email address or pick a user.'
            exc = Invalid(form,message)
            exc['email_addresses']=value['users']=message
            raise exc
        return True
        
    # schema instantiation
    
    def Schema(self):
        # This needs to be a function as we need multi-field validation
        # and some validators needs context
        s = self._Schema(validator=self.users_or_emails).clone()
        s['email_addresses'].validator = self.email_list_validator()
        s['users']['user'].validator=Function(
            self.valid_profile,
            'This is not a valid profile.'
            )
        return s

    def __call__(self):
        # Handle userid passed in via GET request
        # Moderator would get here by clicking a link in an email to grant a
        # user's request to join this community.
        add_user_id = self.request.params.get("user_id")
        if add_user_id is not None:
            profile = self.profiles.get(add_user_id)
            if profile is not None:
                return _add_existing_users(
                    self.context,
                    self.community,
                    [profile,],
                    "",
                    self.request
                    )
        else:
            return super(InviteNewUsersController,self).__call__()

    def form_defaults(self):
        if self.request.params.get('return_to'):
            return {'return_to': self.request.params['return_to']}
        else:
            return null

   
    def handle_submit(self, validated):
        request = self.request
        context = self.context
        community = self.community
        profiles = self.profiles
        
        email_addresses = validated['email_addresses']
        usernames = validated['users']
        
        status = ''
        if email_addresses:
            random_id = getUtility(IRandomId)
            members = community.member_names | community.moderator_names
            community_href = model_url(community, request)
            html_body = validated['text']
            ninvited = nadded = nignored = 0
            
            for email_address in email_addresses:
                profile = self.emails_existing.get(email_address.lower())
                if profile is not None:
                    if profile.__name__ in members:
                        # User is a member of this community, do nothing
                        nignored += 1

                    else:
                        _add_existing_users(context, community, [profile,],
                                            html_body, request)
                        nadded += 1
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
        
       
        if not usernames:
            if request.params.get('return_to') is not None:
                location  = request.params['return_to']
                return render_template_to_response('templates/javascript_redirect.pt', 
                        url=location)

            else:
                location = model_url(context, request, 'manage.html',
                             query={'status_message': status})
                return HTTPFound(location=location)
                
        users = []        
        for username in usernames:
            users.append(self.profiles[username])
        return _add_existing_users(self.context, self.community, users,
                                   validated['text'], self.request, status)


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

class JoinNewUsersController(NewUsersBaseController):

    buttons = ('signup',)

    # schema
    class _Schema(MappingSchema):
        
        email_address = SchemaNode(
                String(),
                )

    def Schema(self):
        # This needs to be a function as some validators needs context
        s = self._Schema().clone()
        s['email_address'].validator=All(
            self.email_validator(),
            # order matters here, since email_validator
            # populates self.emails_existing
            Function(self.email_in_use,
                     'This email address is already registered.'),
            )
        return s

    # validators
    def email_in_use(self,value):
        if value.lower() not in self.emails_existing:
            return True
        
    def handle_submit(self, validated):
        context = self.context
        request = self.request
        random_id = getUtility(IRandomId)
       
        email_address = validated['email_address']
     
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

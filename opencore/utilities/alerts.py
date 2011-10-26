# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz.org
#               2010-2011 Large Blue
#               Fergus Doyle: fergus.doyle@largeblue.com
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

from __future__ import with_statement
from email.mime.multipart import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from lxml import etree
from lxml.html import document_fromstring
from email import Encoders
from traceback import format_exc

import logging
import traceback
from cStringIO import StringIO

import transaction

from zope.component import getMultiAdapter
from zope.component import getUtility, queryUtility
from zope.interface import implements

from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.traversal import find_interface
from repoze.bfg.traversal import find_model
from repoze.bfg.traversal import model_path
from repoze.bfg.url import model_url
from repoze.bfg.settings import asbool
from repoze.sendmail.interfaces import IMailDelivery

from opencore.models.interfaces import IProfile
from opencore.utilities.message import Message
from opencore.utilities.interfaces import IAlert, IAlerts

from opencore.utilities.interfaces import IMessenger
from opencore.models.interfaces import ICommunityContent
from opencore.models.interfaces import IComment
from opencore.utils import find_profiles
from opencore.utils import find_site
from opencore.utils import get_setting
from opencore.models.interfaces import IComment
from opencore.utils import find_community
from opencore.utils import compact_traceback
from opencore.utils import query_count

MAX_ATTACHMENT_SIZE = (1<<20) * 5  # 5 megabytes
log = logging.getLogger(__name__)

def alert_user(profile, event):
    try:
        alerts = queryUtility(IAlerts, default=Alerts())
        alerts.emit_to_user(profile, event)
    except Exception, e:
        log.error('alert_user error for user=%s, event: %s error: (%s) ' % (profile.__name__, 
          str(event), format_exc(e)))

def is_first_entry(context, user):
    first_entry_query = dict(creator=user,
                             interfaces={'query': [ICommunityContent, IComment], 'operator': 'or'},
                             sort_index='modified_date',
                             limit=1)    
    return query_count(context, **first_entry_query) == 0  

class Alerts(object):
    implements(IAlerts)
     
    def emit_to_community(self, event):
        self._emit(event)
        
    def emit_to_user(self, profile, event):
        alerts_on = get_setting(profile, 'alert_notifications_on', 'true')
        if not asbool(alerts_on):
            log.debug('alert notifications are disabled, alert not sent.')
            return
        
        alert = event
        
        # flag alerts are treated differently. Just send straight to admin 
        # not the flagged user.
        if isinstance(alert, FlagAlert):
            log.info('flag alert received. sending directly to admin only.')
            self._send_immediately(alert)
            return
        
        def action_pref(pref, alert):
            if pref == IProfile.ALERT_DIGEST:
                self._queue_digest(alert, profile)
            elif pref == IProfile.ALERT_IMMEDIATELY:
                self._send_immediately(alert)
                
        alerts_inbox_on = get_setting(profile, 'alert_notifications_inbox_on',
                                      'false')
        if not asbool(alerts_inbox_on):
            log.debug('alert inbox notifications are disabled, alert not sent '
                      'to inbox.')
        else:
            # preferences not used for inbox, alert always sent    
            self._send_to_inbox(alert, profile)        
          
        # profile alerts are for content that does not belong to a community 
        # such as profile comments
        if alert.is_profile_alert:
            log.debug('profile alert')
            action_pref(profile.get_alerts_preference('profile'), alert)
            return
        
        community = find_community(event['content'])          
        if community:   
            community_pref = profile.get_alerts_preference(community.__name__)
            log.debug('alert received for user: %s, alert: %s, in community: '
              '%s with pref:%s' % (profile.__name__, str(alert),
                                   community.__name__, community_pref)) 
            action_pref(community_pref, alert)  
            return 
        
        # site preference e.g. for hcd stories                             
        action_pref(profile.get_alerts_preference('site'), alert)
                  
    def _emit(self, event):
        # Get community in which event occurred and alert members
        community = find_community(event['content'])
        if not community:
            log.warning('No community found for event: %s' % str(event))
            return
        profiles = find_profiles(event['content'])
        all_names = community.member_names | community.moderator_names
        for profile in [profiles[name] for name in all_names]:
            self.emit_to_user(profile, community, event)
 
    def _send_to_inbox(self, alert, profile):
        log.info('sending to inbox')
        messenger = getUtility(IMessenger) 
        messenger.send(alert.mfrom, profile, alert.message)   
                      
    def _send_immediately(self, alert):
        log.info('sending mail immediately')
        mailer = getUtility(IMailDelivery)
        mailer.send(alert.mfrom, alert.mto, alert.message)

    def _queue_digest(self, alert, profile):
        log.info('digest mail')
        alert.digest = True
        message = alert.message

        # If message has attachments, body will be list of message parts.
        # First part contains body text, the rest contain attachments.
        if message.is_multipart():  # pragma: no cover
            parts = message.get_payload()
            body = parts[0].get_payload(decode=True)
            attachments = parts[1:]
        else:
            body = message.get_payload(decode=True)
            attachments = []

        profile._pending_alerts.append(
            {"from": message["From"],
             "to": message["To"],
             "subject": message["Subject"],
             "body": body,
             "attachments": attachments})

    def send_digests(self, context):
                
        mailer = getUtility(IMailDelivery)

        system_name = get_setting(context, "system_name", "OpenCore")
        admin_email = get_setting(None, 'admin_email', 'hello@opencore.com')
        #system_email_domain = get_setting(context, "system_email_domain")
        sent_from = admin_email #"%s@%s" % (admin_name, system_email_domain)
        from_addr = "%s notification <%s>" % (system_name, sent_from)
        subject = "%s: Today's Challenge Daily Digest" % system_name
        site_url = get_setting(context, 'public_domain_root', 'http://localhost:6543/')

        template = get_template("email_digest.pt")

        for profile in find_profiles(context).values():
            if not profile._pending_alerts:
                continue

            # Perform each in its own transaction, so a problem with one
            # user's email doesn't block all others
            transaction.manager.begin()
            try:
                attachments = []
                for alert in profile._pending_alerts:
                    attachments += alert['attachments']

                msg = MIMEMultipart() if attachments else Message()
                msg["From"] = from_addr
                msg["To"] = "%s <%s>" % (profile.title, profile.email)
                msg["Subject"] = subject
                profile_url='%sprofiles/%s/' % (site_url, profile.__name__)

                body_text = template(
                    system_name=system_name,
                    alerts=profile._pending_alerts,
                    site_url=site_url,
                    manage_preferences_href=profile_url,
                    creator=profile,
                    profile_image_url='%sprofile_thumbnail' % profile_url,
                    profile_image_thumb_url='%sprofile_thumbnail' % profile_url
                )

                if isinstance(body_text, unicode):
                    body_text = body_text.encode("UTF-8")

                if attachments:  # pragma: no cover
                    body = MIMEText(body_text, 'html', 'utf-8')
                    msg.attach(body)
                else:
                    msg.set_payload(body_text, "UTF-8")
                    msg.set_type("text/html")

                for attachment in attachments:  # pragma: no cover
                    msg.attach(attachment)

                mailer.send(sent_from, [profile.email,], msg)
                del profile._pending_alerts[:]
                transaction.manager.commit()

            except Exception, e:
                # Log error and continue
                log.error("Error sending digest to %s <%s>" %
                          (profile.title, profile.email))

                b = StringIO()
                traceback.print_exc(file=b)
                log.error(b.getvalue())
                b.close()

                transaction.manager.abort()                     
        
class Alert(object):
    """Base adapter class for generating emails from alerts.
    """
    implements(IAlert)

    mfrom = None
    _message = None
    digest = False
    _attachments_folder = None
    _subject = None
    _context = None
    _community = None

    def __init__(self, profile, eventinfo):
        self.eventinfo = eventinfo
        self.profile = profile
        log.debug('Alert: %s, profile=%s, event=%s' % \
                  (self.__class__.__name__, profile, str(eventinfo)))
              
        self.system_name = get_setting(None, "system_name", "OpenCore")
        self.admin_email = get_setting(None, 'admin_email', 'hello@opencore.com')
        self.notifications_reply_to = get_setting(None, 'notifications_reply_to', 'noreply')
        self.system_email_domain = get_setting(None, "system_email_domain")
        self.site_url = get_setting(None, 'public_domain_root',
                                                'http://localhost:6543')
        self.sent_from = self.admin_email 
        self.is_profile_alert = False
 
    @property
    def content(self):
        return self.eventinfo['content']
    
    @property
    def context(self):
        if not self._context:
            self._context = find_model(find_site(self.content),
                                       self.eventinfo['context_url'])
        return self._context
    
    @property
    def community(self):
        if not self._community:
            self._community = find_community(self.context)
        return self._community
       
    @property
    def mto(self):
        return [self.profile.email,]
    
    @property
    def mfrom(self):
        if self._mfrom is not None:
            return self._mfrom

        mfrom = "%s@%s" % (self.eventinfo['context_name'],
                                   self.system_email_domain)
        self._mfrom = mfrom
        return mfrom

    @property
    def message(self):
        if self._message is not None:
            return self._message

        community = self.community
        profile = self.profile
               
        community_href = None
        if community:
            community_href = '%s%s' % (self.site_url, model_path(community))
        manage_preferences_href =  '%s%s' % (self.site_url, model_path(profile))
        system_name = self.system_name
        system_email_domain = self.system_email_domain
        reply_to = "%s <%s@%s>" % (system_name, self.notifications_reply_to,
                                   system_email_domain)

        attachments, attachment_links, attachment_hrefs = self.attachments
        log.debug('create message using template: %s' % self._template)
        body_template = get_template(self._template)
        from_name = "%s notification" % system_name
        msg = MIMEMultipart() if attachments else Message()
        msg["From"] = "%s <%s>" % (from_name, self.mfrom)
        msg["To"] = "%s <%s>" % (profile.title, profile.email)
        if isinstance(self, FlagAlert):
            msg["To"] = "%s <%s>" % ('Admin', self.mto)
        msg["Reply-to"] = reply_to
        msg["Subject"] = self._subject
        body_text = body_template(
            context=self.context,
            community=community,
            community_href=community_href,
            attachments=attachment_links,
            attachment_hrefs=attachment_hrefs,
            manage_preferences_href=manage_preferences_href,
            profile=profile,
            digest=self.digest,
            alert=self,
            eventinfo=self.eventinfo,
            history=self._history,
            site_url=self.site_url,
            model_path=model_path,
            system_name=system_name
        )

        if self.digest:
            # Only interested in body for digest
            html = document_fromstring(body_text)
            body_element = html.cssselect('body')[0]
            span = etree.Element("span", nsmap=body_element.nsmap)
            span[:] = body_element[:] # Copy all body elements to an empty span
            body_text = etree.tostring(span, pretty_print=True)

        if isinstance(body_text, unicode):
            body_text = body_text.encode('utf-8')

        if attachments:  # pragma: no cover
            body = MIMEText(body_text, 'html', 'utf-8')
            msg.attach(body)
            for attachment in attachments:
                msg.attach(attachment)
        else:
            msg.set_payload(body_text, 'utf-8')
            msg.set_type("text/html")

        self._message = msg

        return self._message

    @property
    def _attachments_folder(self):
        return self.content.get('attachments')

    @property
    def _history(self):
        """
        Return a tuple, (messages, n), where messages is a list of at most
        three preceding messages considered relevant to the current message. n
        is the total number of messages in the 'thread' for some definition of
        'thread'.
        """
        return ([], 0)

    @property
    def attachments(self):  # pragma: no cover
        folder = self._attachments_folder
        if folder is None:
            return [], [], {}

        profile = self.profile
        request = self.request
        attachments = []
        attachment_links = []
        attachment_hrefs = {}
        for name, model in folder.items():
            if profile.alert_attachments == 'link':
                attachment_links.append(name)
                attachment_hrefs[name] = model_url(model, request)

            elif profile.alert_attachments == 'attach':
                with model.blobfile.open() as f:
                    f.seek(0, 2)
                    size = f.tell()
                    if size > MAX_ATTACHMENT_SIZE:
                        attachment_links.append(name)
                        attachment_hrefs[name] = model_url(model, request)

                    else:
                        f.seek(0, 0)
                        data = f.read()
                        type, subtype = model.mimetype.split('/', 1)
                        attachment = MIMEBase(type, subtype)
                        attachment.set_payload(data)
                        Encoders.encode_base64(attachment)
                        attachment.add_header(
                            'Content-Disposition',
                            'attachment; filename="%s"' % model.filename)
                        attachments.append(attachment)

        return attachments, attachment_links, attachment_hrefs


class CommentAlert(Alert):
    _template = "templates/email_comment_alert.pt"
      
    def __init__(self, profile, eventinfo):
        super(CommentAlert, self).__init__(profile, eventinfo)
        assert IComment.providedBy(self.content)
        self._mfrom = self.sent_from
        if find_interface(self.content, IProfile):
             # set the community to profile for now 
            self._template = "templates/email_profile_comment_alert.pt"
            self.is_profile_alert = True
       
    @property
    def _subject(self):
        if self.content.is_reply:
            return '%s: Someone added to a comment you made' % (self.system_name)
        elif self.is_profile_alert:
            return '%s: Someone commented  on your profile' % (self.system_name)
        else: 
            return '%s: Someone commented  on your %s' % (self.system_name,
                    self.eventinfo['content_type'])

    @property
    def _history(self):
        """ See abstract base class, BlogAlert, above."""
        if self.digest:
            return ([], 0)

        blogentry = self.context
        comments = list(self.context['comments'].values())
        comments = [comment for comment in comments
                    if comment is not self.context]
        comments.sort(key=lambda x: x.created)
        comments.reverse()

        messages = [blogentry] + comments
        n = len(comments) + 1
        return messages, n

class FlagAlert(Alert):
    _template = "templates/email_flag_alert.pt"
         
    def __init__(self, profile, eventinfo):
        super(FlagAlert, self).__init__(profile, eventinfo)
        self._mfrom = self.sent_from
        if find_interface(self.content, IProfile):
            # comments can be flagged against a profile 
            log.debug('FlagAlert set against a profile.')
            self._template = "templates/email_profile_flag_alert.pt"
            self.is_profile_alert = True
    
    @property
    def mto(self):
        # send to admin user for flags
        return [self.admin_email,]
    
    @property
    def _subject(self):
        if self.is_profile_alert:
            return '%s Administrator: Inappropriate comment reported' % self.system_name
        else:
            return '%s Administrator: Inappropriate %s reported' % (self.system_name,
              self.eventinfo['content_type'])
        
    @property
    def _attachments_folder(self):
        return None
    

def eventinfo_alert_factory(profile, eventinfo):
    '''
    create an alert based on eventinfo received
    here is an example of joe making a comment to story (in hcd) 
    Note: content_creator shows 'admin' here instead of joe as its a special case when content=Comment
    to get the user filter were creator='admin' to show comments made.  
    (eventinfo)
    {
    'description': u'another great story to end',
    'tags': [],
    'timestamp': datetime.datetime(2011, 5, 7, 14, 35, 37, 70457),
    'context_creator': 'admin',
    'url': '/stories/selling-more-treadle-pumps-by-designing-posters-with-farmers/comments/009',
    'content_type': 'Comment',
    'allowed': set(['group.KarlStaff', 'group.KarlModerator', 'group.KarlAdmin', 'system.Authenticated', 'group.KarlUserAdmin']),
    'context_name': u'Selling more treadle pumps by designing posters with farmers',
    'context_url': '/stories/selling-more-treadle-pumps-by-designing-posters-with-farmers',
    'title': u'Re: Selling more treadle pumps by designing posters with farmers',
    'context_type': 'Story',
    'author': u'Joe Marks',
    'userid': u'joe',
    'content': <opencore.models.commenting.Comment object u'009' at 0x10146d1b8>,
    'content_creator': 'admin',
    'comment_count': 0,
    'short_description': u'another great story to end',
    'thumbnail': u'/profiles/joe/profile_thumbnail',
    'profile_url': u'/profiles/joe'
    }
    
    joe project comment reply from admin 
    {
    'description': u'goodbye',
    'tags': [],
    'timestamp': datetime.datetime(2011, 5, 8, 9, 37, 29, 900983),
    'context_creator': 'admin',
    'url': '/projects/using-mobile-phones-to-bring-crops-to-market-more-effectively/comments/006/comments/001',
    'content_type': 'Comment',
    'allowed': set(['group.KarlStaff', 'admin', 'group.KarlUserAdmin', 'group.KarlModerator', 'group.KarlAdmin', u'group.community:using-mobile-phones-to-bring-crops-to-market-more-effectively:moderators', 'system.Authenticated', u'group.community:using-mobile-phones-to-bring-crops-to-market-more-effectively:members']),
    'context_name': u'Using mobile phones to bring crops to market more effectively',
    'context_url': '/projects/using-mobile-phones-to-bring-crops-to-market-more-effectively',
    'title': u'Re: Re: Using mobile phones to bring crops to market more effectively',
    'context_type': 'Project',
    'author': u'Ad Min',
    'userid': u'admin',
    'content': <opencore.models.commenting.Comment object u'001' at 0x10676bc80>,
    'content_creator': u'joe',
    'comment_count': 0,
    'short_description': u'goodbye',
    'thumbnail': u'/profiles/admin/profile_thumbnail',
    'profile_url': u'/profiles/admin'
    }
    
    profile comment
    {
    'context_url': '/profiles/joe', 
    'description': u"joe's a good guy", 
    'tags': [], 
    'url': '/profiles/joe/comments/001', 
    'timestamp': datetime.datetime(2011, 5, 2, 10, 31, 52, 968337), 
    'title': u'Re: Joe Marks', 
    'userid': u'admin', 
    'thumbnail': u'/profiles/admin/profile_thumbnail', 
    'content_creator': u'joe', 
    'comment_count': 0, 
    'author': u'Ad Min', 
    'content_type': 'Comment', 
    'allowed': set(['group.KarlStaff', 'system.Authenticated', 'group.KarlUserAdmin', u'joe', 'group.KarlAdmin']), 
    'short_description': u"joe's a good guy", 
    'context_name': u'Joe Marks', 
    'operation': 'added', 
    'flavor': 'added_edited_other', 
    'profile_url': u'/profiles/admin'
    }
    '''
    alert = None
    if eventinfo['content_type'] == 'Comment':
        alert = CommentAlert(profile, eventinfo)
    return alert
            
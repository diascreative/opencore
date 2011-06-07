
# stdlib
import logging
import traceback
from operator import itemgetter, attrgetter
from datetime import datetime
from time import strftime, strptime
from traceback import format_exc

# Zope
import transaction
from zope.component import getUtility
from zope.interface import implements

# webob
from webob import Response

# Repoze
from repoze.bfg.security import authenticated_userid

# simplejson
from simplejson import JSONEncoder

# opencore
from opencore.models.interfaces import IEventInfo
from opencore.models.interfaces import IProfileDict
from opencore.models.mbox import(ALLOWED_MBOX_TYPES, DEFAULT_MBOX_TYPE,
            TO_SEPARATOR, STATUS_READ)
from opencore.utilities.alerts import alert_user
from opencore.utilities.mbox import MailboxTool
from opencore.utilities.mbox import MboxMessage
from opencore.utilities.paginate import Pagination
from opencore.utils import find_profiles
from opencore.utils import get_setting

from openhcd.views.utils import find_site

"""
Views API
---------

- return a list of Queues /mbox.html
  - input:
        mailbox type (inbox/sent) [mbox_type],
        page number [page]
  - output:
        template API [api],
        list of Queue objects [queues], each object has:
          Queue ID [id],
          Queue name [name],
          number of Messages in the Queue [total_messages],
          from header of the first Message [first_message_from],
          to header of the first Message [first_message_to],
          date header of the first Message [first_message_date],
          mailbox type (inbox/sent) [mbox_type]

- return a list of Messages for the given Queue /mbox_thread.html
  - input:
        mailbox type (inbox/sent) [mbox_type],
        Queue ID [thread_id]
  - output:
        template API [api],
        mailbox type (inbox/sent) [mbox_type],
        list of Messages (possibly one-element in length only) [messages], each object has:
          ID of the Queue it belongs to [queue_id],
          Message ID [message_id],
          subject [subject],
          date header [date],
          flags [flags],
          user name of the person from the from header [from],
          first & last name of the person from the from header [from_firstname] [from_lastname],
          link to profile picture of the person from the from header [from_photo],
          country code of the person from the from header [from_country],
          payload [payload],
          for each person in the Message's to header [to_data]:
            user name [name],
            first & last name [firstname] [lastname],
            link to profile picture [photo_url],
            country code [country]

- add a new Message: /mbox_add_message.html
  - input:
        a comma-separated list of 'to: ' users [to],
        subject (aka the name of the message) [subject],
        the actual payload [payload]
  - output:
        template API [api],
        boolean flag indicating whether it's succeeded or not [success],
        message (Python exception) explaining the failure reason if not success [error_msg,
        mailbox type (inbox/sent) [mbox_type]

- delete a Message (AJAX call) /mbox_delete_message.html
  - input:
        mailbox type (inbox/sent) [mbox_type],
        Queue ID [thread_id],
        message ID [message_id]
  - output:
        boolean flag indicating whether it's succeeded or not [success],
        message (Python exception) explaining the failure reason if not success [error_msg],

- mark a Message read (AJAX call) /mbox_mark_message_read.html
  Note: marking a message read twice is a no-op
  - input:
        mailbox type (inbox/sent) [mbox_type],
        Queue ID [thread_id],
        message ID [message_id]
  - output:
        boolean flag indicating whether it's succeeded or not [success],
        message (Python exception) explaining the failure reason if not success [error_msg]
"""

# How many queues per page to show?
PER_PAGE = 20

log = logging.getLogger(__name__)

class _MBoxEvent(dict):
    implements(IEventInfo)
    is_profile_alert = False

def _format_date(context, date):
    date = ''.join(date.split('.')[0])

    date_format_from = get_setting(context, 'messaging_date_format_from')
    date_format_to = get_setting(context, 'messaging_date_format_to')

    return strftime(date_format_to, strptime(date, date_format_from))

def _json_response(success, error_msg):
    return_data = {}
    return_data['success'] = success
    return_data['error_msg'] = error_msg

    result = JSONEncoder().encode(return_data)
    return Response(result, content_type='application/x-json')

def _get_mbox_type(request):
    mbox_type = request.params.get('mbox_type', '')

    # Guard against abuses.
    if not mbox_type:
        mbox_type = DEFAULT_MBOX_TYPE

    if not mbox_type in ALLOWED_MBOX_TYPES:
        mbox_type = DEFAULT_MBOX_TYPE

    return mbox_type

def _user_photo_url(request, user): 
    profile = request.api.find_profile(user)
    return profile.thumb_url(request)

def _to_from_to_header(message):
    addresses = message.get('To', '').split(TO_SEPARATOR)
    return [elem.strip() for elem in addresses]

def _get_profile_details(context, request, user):
    profile = request.api.find_profile(user)
    profile_details = getUtility(IProfileDict, name='profile-details')
    profile_details.update_details(profile, request, request.api, (220,150))

    return profile_details

def show_mbox(context, request):
    user = authenticated_userid(request)

    page = request.params.get('page', 1)
    mbox_type = _get_mbox_type(request)

    if not page:
        page = 1

    try:
        page = int(page)
    except ValueError:
        page = 1

    if page < 1:
        page = 1

    mbt = MailboxTool()
    mbox_queues = mbt.get_queues(context, user, mbox_type)
    alternate_mbox_type = 'sent' if mbox_type == 'inbox' else 'inbox'
    unread = mbt.get_unread(context, user, 'inbox')

    pagination = Pagination(page, PER_PAGE, len(mbox_queues))

    # We always count lists from 0, unlike what people do.
    actual_page = page - 1

    # First page ..
    if actual_page == 0:
        start_idx = 0
        end_idx = PER_PAGE

    # .. last page ..
    if not pagination.has_next:
        start_idx = actual_page * PER_PAGE
        end_idx = pagination.total_count

    # .. anything in between
    else:
        start_idx = actual_page * PER_PAGE
        end_idx = (actual_page + 1) * PER_PAGE

    queues = []
    for mbox_q in mbox_queues[start_idx:end_idx]:
        queue = {}
        queue['id'] = mbox_q.id
        queue['name'] = mbox_q.name
        messages = list(mbox_q)
        if mbt.has_queue(context, user, alternate_mbox_type, queue['id']):
            alternate_queue, _, _ = mbt.get_queue_data(context, user,
                    alternate_mbox_type, queue['id'])
            messages += list(alternate_queue)

        sender_names = get_sender_names(request, user, messages)

        queue['total_messages'] = len(messages)
        queue['thread_from'] = ', '.join(sender_names)
        last_message = messages[queue['total_messages'] - 1]
        queue['thread_last_date'] = _format_date(context, last_message['Date'])
        queue['unread'] = mbox_q.get_unread()


        queues.append(queue)

    return_data = {}
    return_data['profile'] = _get_profile_details(context, request, user)
    return_data['queues'] = queues
    return_data['api'] = request.api
    return_data['mbox_type'] = mbox_type
    return_data['unread'] = unread
    return_data['page'] = page

    return return_data

def get_sender_names(request, user, messages):
    messages.sort(key=itemgetter('Date'))
    senders = set(message['From'] for message in messages 
                  if message['From'] != user)
    display_attr = 'firstname' if len(senders) > 1 else 'fullname'
    sender_names = []
    for sender in senders:
        profile = request.api.find_profile(sender)
        if profile is not None:
            sender_names.append(getattr(profile, display_attr))
        else:
            sender_names.append(sender)
    return sender_names

def show_mbox_thread(context, request):
    user = authenticated_userid(request)

    thread_id = request.params.get('thread_id', '')
    mbox_type = _get_mbox_type(request)

    mbt = MailboxTool()
    queues = []
    if mbt.has_queue(context, user, 'inbox', thread_id):
        inbox_q, _, _ = mbt.get_queue_data(context, user, 'inbox', thread_id)
        queues.append(inbox_q)
    if mbt.has_queue(context, user, 'sent', thread_id):
        sent_q, _, _ = mbt.get_queue_data(context, user, 'sent', thread_id)
        queues.append(sent_q)
    unread = mbt.get_unread(context, user, 'inbox')

    messages = []

    reply_recipients = set()

    for q in queues:
        for msg_no in q._messages:
            msg_dict = {}
            raw_msg = q._messages[msg_no]
            raw_msg.flags.append(STATUS_READ)
            message = raw_msg.get()
            from_ = message['From']
            from_profile = request.api.find_profile(from_)

            msg_dict['queue_id'] = q.id
            msg_dict['message_id'] = raw_msg.message_id
            msg_dict['raw_date'] = message['Date']
            msg_dict['date'] = _format_date(context, message['Date'])
            msg_dict['subject'] = message['Subject']
            msg_dict['flags'] = raw_msg.flags

            msg_dict['from'] = from_
            if from_ != user:
                reply_recipients.add(from_)
            msg_dict['from_photo'] = _user_photo_url(request, message['From'])
            msg_dict['from_firstname'] = from_profile.firstname
            msg_dict['from_lastname'] = from_profile.lastname
            msg_dict['from_country'] = from_profile.country
            msg_dict['from_organization'] = from_profile.organization
            msg_dict['payload'] = message.get_payload().decode('utf-8')

            to_data = []
            for name in sorted(_to_from_to_header(message)):
                to_datum = {}
                to_profile = request.api.find_profile(name)

                to_datum['name'] = name
                to_datum['firstname'] = to_profile.firstname
                to_datum['lastname'] = to_profile.lastname
                to_datum['photo_url'] = _user_photo_url(request, name)
                to_datum['country'] = to_profile.country
                to_data.append(to_datum)

            msg_dict['to_data'] = to_data

            messages.append(msg_dict)

    messages.sort(key=itemgetter('raw_date'))

    return_data = {}
    return_data['profile'] = _get_profile_details(context, request, user)
    return_data['messages'] = messages
    return_data['api'] = request.api
    return_data['mbox_type'] = mbox_type
    return_data['unread'] = unread
    return_data['reply_recipients'] = reply_recipients

    return return_data


def send_to(context, request, to):
    user = authenticated_userid(request)

    now = str(datetime.utcnow())

    subject = request.POST.get('subject', '')
    payload = request.POST.get('payload', '')
    thread_id = request.POST.get('thread_id')

    mbt = MailboxTool()

#   FIXME not sure if this is actually used
#    unread = mbt.get_unread(context, user, 'inbox')
#    return_data['unread'] = unread

    msg = MboxMessage(payload.encode('utf-8'))
    msg['Message-Id'] = MailboxTool.new_message_id()
    if thread_id is None:
        msg['Subject'] = subject
        # We'll setup the subject automatically if it's a reply
    msg['From'] = user
    msg['To'] = to
    msg['Date'] = now
    msg['X-oc-thread-id'] = thread_id or MailboxTool.new_thread_id()

    site = find_site(context)
    to_profile = request.api.find_profile(to)
    from_profile = request.api.find_profile(user)
    if thread_id is None:
        mbt.send_message(site, user, to_profile, msg)
    else:
        mbt.send_reply(site, thread_id, user, to_profile, msg)

    eventinfo = _MBoxEvent()
    eventinfo['content'] = msg
    eventinfo['content_type'] = 'MBoxMessage'
    eventinfo['context_url'] = from_profile.__name__

    eventinfo.mfrom = from_profile.__name__
    eventinfo.mfrom_name = from_profile.__name__
    eventinfo.mto = [to_profile.email]
    eventinfo.message = msg

    alert_user(to_profile, eventinfo)




def add_message(context, request):

    mbox_type = _get_mbox_type(request)

    return_data = {}
    return_data['error_msg'] = ''
    return_data['success'] = False
    return_data['api'] = request.api
    return_data['mbox_type'] = mbox_type
    user = authenticated_userid(request)
    return_data['profile'] = _get_profile_details(context, request, user)

    if request.method == 'POST':
        recipients_list = request.POST.getall('to[]')
        try:
            for recipient in recipients_list:
                send_to(context, request, recipient)
        except Exception, e:
            error_msg = "Couldnt't add a new message, e=[%s]" % traceback.format_exc(e)
            log.error(error_msg)
            return_data['error_msg'] = error_msg
            transaction.abort()
            success = False
        else:
            transaction.commit()
            success = True

        return_data['success'] = success


    return return_data

def delete_message(context, request):

    user = authenticated_userid(request)

    success = False
    error_msg = ''

    thread_id = request.POST.get('thread_id', '')
    message_id = request.POST.get('message_id', '')
    mbox_type = _get_mbox_type(request)

    mbt = MailboxTool()

    try:
        mbt.delete_message(context, user, mbox_type, thread_id, message_id)
    except Exception, e:
        error_msg = format_exc(e)
    else:
        success = True

    return _json_response(success, error_msg)

def delete_thread(context, request):

    user = authenticated_userid(request)

    success = False
    error_msg = ''

    thread_id = request.params.get('thread_id', '')
    mbox_type = _get_mbox_type(request)

    mbt = MailboxTool()

    try:
        mbt.delete_thread(context, user, mbox_type, thread_id)
    except Exception, e:
        error_msg = format_exc(e)
    else:
        success = True

    return _json_response(success, error_msg)

def mark_message_read(context, request):

    user = authenticated_userid(request)

    success = False
    error_msg = ''

    thread_id = request.params.get('thread_id', '')
    message_id = request.params.get('message_id', '')
    mbox_type = _get_mbox_type(request)

    mbt = MailboxTool()

    try:
        raw_msg, msg = mbt.get_message(context, user, mbox_type, thread_id, message_id)
        if not STATUS_READ in raw_msg.flags:
            raw_msg.flags.append(STATUS_READ)
    except Exception, e:
        error_msg = format_exc(e)
    else:
        success = True

    return _json_response(success, error_msg)

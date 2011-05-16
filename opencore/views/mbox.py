
# stdlib
from datetime import datetime
from email import utils
from traceback import format_exc

# Zope
import transaction

# webob
from webob import Response
from webob.exc import HTTPUnauthorized

# Repoze
from repoze.bfg.security import authenticated_userid

# simplejson
from simplejson import JSONEncoder

# opencore
from opencore.models.mbox import(ALLOWED_MBOX_TYPES, DEFAULT_MBOX_TYPE, 
            TO_SEPARATOR, STATUS_READ, ALLOWED_STATUSES)
from opencore.utilities.mbox import MailboxTool
from opencore.utilities.mbox import MboxMessage
from opencore.utilities.paginate import Pagination

# How many queues per page to show?
PER_PAGE = 20

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
    return '%s/%s/profile_thumbnail' % (request.api.people_url, user)

def _to_from_to_header(message):
    addresses = message.get('To', '').split(TO_SEPARATOR)
    return [elem.strip() for elem in addresses]

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
        queue['total_messages'] = len(mbox_q)
        
        first_message = mbox_q.get(0)
        
        queue['first_message_from'] = first_message['From']
        queue['first_message_to'] = _to_from_to_header(first_message)
        queue['first_message_date'] = first_message['Date']
        
        queues.append(queue)
    
    return_data = {}
    return_data['queues'] = queues
    return_data['api'] = request.api
    
    return return_data

def show_mbox_thread(context, request):
    user = authenticated_userid(request)
    
    thread_id = request.params.get('thread_id', '')
    mbox_type = _get_mbox_type(request)

    mbt = MailboxTool()
    q, _, _ = mbt.get_queue_data(context, user, mbox_type, thread_id)

    messages = []
    
    for msg_no in q._messages:
        msg_dict = {}
        raw_msg = q._messages[msg_no]
        message = raw_msg.get()
        from_ = message['From']
        from_profile = request.api.find_profile(from_)
        
        msg_dict['queue_id'] = q.id
        msg_dict['message_id'] = raw_msg.message_id
        msg_dict['date'] = message['Date']
        msg_dict['flags'] = raw_msg.flags
        
        msg_dict['from'] = from_
        msg_dict['from_photo'] = _user_photo_url(request, message['From'])
        msg_dict['from_firstname'] = from_profile.firstname
        msg_dict['from_lastname'] = from_profile.lastname
        msg_dict['from_country'] = from_profile.country
        msg_dict['payload'] = message.get_payload()
        
        to_data = []
        for name in sorted(_to_from_to_header(message)):
            to_datum = {}
            to_profile = request.api.find_profile(name)
            
            to_datum['name'] = name
            to_datum['firstname'] = to_profile.firstname
            to_datum['lastname'] = to_profile.lastname
            to_datum['country'] = to_profile.country
            to_datum['photo_url'] = _user_photo_url(request, name)
            to_data.append(to_datum)
            
        msg_dict['to_data'] = to_data
        
        messages.append(msg_dict)
    
    return_data = {}
    return_data['messages'] = messages
    return_data['api'] = request.api
    
    return return_data

def add_message(context, request):
    
    user = authenticated_userid(request)
    
    success = False
    error_msg = ''

    now = str(datetime.utcnow())
    to = request.POST['to']
    to = [elem.strip() for elem in to.split(',')]
    
    subject = request.POST['subject']
    payload = request.POST['payload']
    
    mbt = MailboxTool()
    
    msg = MboxMessage('aa')
    msg['Message-Id'] = MailboxTool.new_message_id()
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = ', '.join(to)
    msg['Date'] = now
    msg['X-oc-thread-id'] = MailboxTool.new_thread_id()
    
    try:
        mbt.send_message(context, user, to, msg)
        transaction.commit()
    except Exception, e:
        error_msg = str(e)
        transaction.rollback()
    else:
        success = True
    
    return_data = {}
    return_data['success'] = success
    return_data['error_msg'] = error_msg
    return_data['api'] = request.api
    
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

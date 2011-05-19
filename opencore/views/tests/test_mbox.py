
# stdlib
import unittest, uuid
from datetime import datetime

# Zope
import transaction

# webob
from webob import Response

# Repoze
from repoze.bfg import testing
from repoze.folder import Folder

# testfixtures
from testfixtures import LogCapture
from testfixtures import Replacer

# simplejson
from simplejson import JSONDecoder

# opencore
from opencore.scripting import get_default_config
from opencore.scripting import open_root
from opencore.utilities.mbox import MailboxTool
from opencore.utilities.mbox import MboxMessage
from opencore.utilities.mbox import NoSuchThreadException
from opencore.utilities.tests.test_mbox import get_data
from opencore.views.mbox import _get_mbox_type
from opencore.views.mbox import _json_response
from opencore.views.mbox import DEFAULT_MBOX_TYPE
from opencore.views.mbox import PER_PAGE
from opencore.views.mbox import add_message
from opencore.views.mbox import delete_message
from opencore.views.mbox import mark_message_read
from opencore.views.mbox import show_mbox
from opencore.views.mbox import show_mbox_thread

def _authenticated_user_id(request):
    return 'admin'

class MBoxViewTestCase(unittest.TestCase):
    
    def setUp(self):
        self.mbt = MailboxTool()
        self.log = LogCapture()
    
    def tearDown(self):
        testing.cleanUp()
    
    def _get_mbox_request(self, mbox_type, key='mbox_type'):
        request = testing.DummyRequest()
        request.params[key] =  mbox_type
        
        return request

    def test_per_page(self):
        self.assertEquals(PER_PAGE, 20)
    
    def test_json_response(self):
        success = uuid.uuid4().hex
        error_msg = uuid.uuid4().hex
        
        response = _json_response(success, error_msg)
        
        self.assertTrue(isinstance(response, Response))
        self.assertEquals(response.content_type, 'application/x-json')
        
        given_body = sorted(JSONDecoder().decode(response.body).items())
        expected_body = [('error_msg', error_msg), ('success', success)]
        self.assertEquals(given_body, expected_body)
        
    def test_get_mbox_type(self):
        mbox_type = _get_mbox_type(self._get_mbox_request('inbox'))
        self.assertEquals(mbox_type, 'inbox')
        
        mbox_type = _get_mbox_type(self._get_mbox_request('sent'))
        self.assertEquals(mbox_type, 'sent')
        
        # Unrecognized mbox type, should revert to default inbox.
        mbox_type = _get_mbox_type(self._get_mbox_request(uuid.uuid4().hex))
        self.assertEquals(mbox_type, DEFAULT_MBOX_TYPE)
        
        # Unrecognized key, should revert to default inbox.
        mbox_type = _get_mbox_type(self._get_mbox_request('inbox', key=uuid.uuid4().hex))
        self.assertEquals(mbox_type, DEFAULT_MBOX_TYPE)
        
    def test_show_mbox(self):
        
        with Replacer() as r:
            r.replace('opencore.views.mbox.authenticated_userid', _authenticated_user_id)
            
            # Different from what the msg has in its 'To: ' header
            # but we need it because that's what our 'authenticated_userid' uses.
            to = ['admin'] 
            
            site, from_, _, msg, _, _, _, _, _, _ = get_data()
            self.mbt.send_message(site, from_, to, msg, should_commit=True)
        
            site, _ = open_root(get_default_config())
            request = testing.DummyRequest()
            request.api = uuid.uuid4().hex
            
            response = show_mbox(site, request)

            self.assertTrue(response.get('api', None) is not None)
            
            if not response['queues']:
                raise Exception('No queues found in the response %s' % response)
            
            for q in response['queues']:
                self.assertTrue(q['total_messages'] >= 1)
                self.assertTrue(len(q['first_message_to']) >= 1)
                self.assertTrue(len(q['name']) >= 1)
                self.assertTrue(q['first_message_from'] == 'admin')
                
                # To anyone changing it and discovering the assertion
                # failing here - please use a UUID4 if possible (why wouldn't 
                # it be possible?)
                self.assertTrue(len(q['id']) >= 20)
                
    def zztest_show_mbox(self):
        
        _people_url = uuid.uuid4().hex
        _firstname = uuid.uuid4().hex
        _lastname = uuid.uuid4().hex
        _country = uuid.uuid4().hex
        
        class _DummyAPI(object):
            def find_profile(*ignored_args, **ignored_kwargs):
                class _Dummy(object):
                    firstname = _firstname
                    lastname = _lastname
                    country = _country
                    
                return _Dummy()
            
            people_url = _people_url
        
        with Replacer() as r:
            r.replace('opencore.views.mbox.authenticated_userid', _authenticated_user_id)
            
            # Different from what the msg has in its 'To: ' header
            # but we need it because that's what our 'authenticated_userid' uses.
            to = ['admin'] 
            
            site, from_, _, msg, thread_id, _, _, _, payload, _ = get_data()
            self.mbt.send_message(site, from_, to, msg, should_commit=True)
        
            site, _ = open_root(get_default_config())
            request = testing.DummyRequest()
            request.params['thread_id'] = thread_id
            request.api = _DummyAPI()
            
            response = show_mbox_thread(site, request)
            
            self.assertTrue(isinstance(response['api'], _DummyAPI))
            
            self.assertTrue(len(response['messages']), 1)
            message = response['messages'][0]

            flags = message['flags']
            if flags:
                self.assertEquals(flags, ['READ'])
                
            self.assertEquals(message['from'], 'admin')
            self.assertEquals(message['from_country'], _country)
            self.assertEquals(message['from_firstname'], _firstname)
            self.assertEquals(message['from_lastname'], _lastname)
            self.assertEquals(message['from_photo'], _people_url + '/admin/profile_thumbnail')
            self.assertEquals(message['payload'], payload)
            self.assertTrue(len(message['payload']) > 20)
            self.assertTrue(len(message['queue_id']) > 20)
            
            self.assertTrue(len(message['to_data']) == 2)
            to_data = message['to_data']
            
            for to_datum in to_data:
                self.assertEquals(to_datum['country'], _country)
                self.assertEquals(to_datum['firstname'], _firstname)
                self.assertEquals(to_datum['lastname'], _lastname)
                
                name = to_datum['name']
                self.assertTrue(name in ('joe', 'sarah'))
                self.assertEquals(to_datum['photo_url'], _people_url + '/' + name + '/profile_thumbnail')
                
    def zztest_add_message(self):
        
        to = 'joe, sarah'
        
        subject = uuid.uuid4().hex
        payload = uuid.uuid4().hex
        api = uuid.uuid4().hex
        
        site, _ = open_root(get_default_config())
        
        with Replacer() as r:
            r.replace('opencore.views.mbox.authenticated_userid', _authenticated_user_id)
            
            request = testing.DummyRequest()
            request.api = api
            request.POST['to'] = to
            request.POST['subject'] = subject
            request.POST['payload'] = payload
            
            response = add_message(site, request)
            self.assertEquals(response['api'], api)
            self.assertEquals(response['error_msg'], '')
            self.assertEquals(response['success'], True)
            
            transaction.commit()
            
    def zztest_delete_message(self):
        
        api = uuid.uuid4().hex
        
        with Replacer() as r:
            r.replace('opencore.views.mbox.authenticated_userid', _authenticated_user_id)
            
            to = ['admin'] 
            site, from_, _, msg, thread_id, msg_id, _, _, _, _ = get_data()
            self.mbt.send_message(site, from_, to, msg, should_commit=True)
            
            request = testing.DummyRequest()
            request.api = api
            request.params['thread_id'] = thread_id
            request.params['message_id'] = msg_id
            
            delete_message(site, request)
            transaction.commit()
            
            try:
                raw_msg, msg = self.mbt.get_message(site, from_, 'inbox', thread_id, msg_id)
            except NoSuchThreadException:
                pass
            else:
                raise Exception('Expected a NoSuchThreadException here')
            
    def zztest_mark_message_read(self):
        
        api = uuid.uuid4().hex
        
        with Replacer() as r:
            r.replace('opencore.views.mbox.authenticated_userid', _authenticated_user_id)
            
            to = ['admin'] 
            site, from_, _, msg, thread_id, msg_id, _, _, _, _ = get_data()
            self.mbt.send_message(site, from_, to, msg, should_commit=True)
            
            request = testing.DummyRequest()
            request.api = api
            request.params['thread_id'] = thread_id
            request.params['message_id'] = msg_id
            
            mark_message_read(site, request)
            transaction.commit()
            
            raw_msg, msg = self.mbt.get_message(site, from_, 'inbox', thread_id, msg_id)
            self.assertEquals(raw_msg.flags, ['READ'])
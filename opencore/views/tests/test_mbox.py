
# stdlib
import unittest, uuid
from datetime import datetime

# webob
from webob import Response

# Repoze
from repoze.bfg import testing
from repoze.folder import Folder

# simplejson
from simplejson import JSONDecoder

# opencore
from opencore.scripting import get_default_config
from opencore.scripting import open_root
from opencore.utilities.mbox import MailboxTool
from opencore.utilities.mbox import MboxMessage
from opencore.views.mbox import _get_mbox_type
from opencore.views.mbox import _json_response
from opencore.views.mbox import DEFAULT_MBOX_TYPE
from opencore.views.mbox import PER_PAGE


class MBoxViewTestCase(unittest.TestCase):
    
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
        
'''
class AjaxViewTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()
        
    def tearDown(self):
        testing.cleanUp()
          
    def _callFUT(self, context, request):
        from opencore.views.mbox import MboxView
        mbox_view = MboxView(context, request)
        return mbox_view.queue_view(context, request)    

    def zztest_view_callable(self):
        from opencore.views.mbox import MboxView
        request = testing.DummyRequest()
        context = testing.DummyModel()
        context.__name__ = None
        mbox_view = MboxView(context, request)
        response = mbox_view()  
        self.assertEqual(response.headerlist[0],
                         ('Content-Type', 'application/x-json'))
        self.assertEqual(response.app_iter[0], '{}')    
        
              
    def zztest_empty_queue(self):
        request = testing.DummyRequest()
        response = self._callFUT([], request)
        self.assertEqual(response.headerlist[0],
                         ('Content-Type', 'application/x-json'))
        self.assertEqual(response.app_iter[0], '{}')
        
        
    def zztest_msgs_in_queue(self): 
        from opencore.utilities.message import MboxMessage 
        import simplejson as json

        request = testing.DummyRequest()
        messages = ({'payload' :'hello', 'From' : 'niceguy', "flags": "S"}, 
                    {'payload': 'goodbye', 'From' : 'afoe', "flags": "F" })
        request.context = {}
        for i in range(len(messages)):
            request.context[i] = MboxMessage(messages[i]['payload'])
            request.context[i]['From'] = messages[i]['From']
            request.context[i].set_flags(messages[i]['flags'])
            
        input =  {'0': messages[0], 
                  '1': messages[1]}
        input['0']['date'] = request.context[0].get_date()
        input['1']['date'] = request.context[1].get_date()    
        
        response = self._callFUT(request.context, request)
        self.assertEqual(response.headerlist[0],
                         ('Content-Type', 'application/x-json'))
        json_payload = response.app_iter[0]
        self.assertEqual(json.loads(json_payload), input)
        
    def zztest_modify_queue(self):
        from opencore.utilities.message import MboxMessage 
        request = testing.DummyRequest(post={1 : {'flags' : 'FS'}})
        messages = ({'payload' :'hello', 'From' : 'niceguy', "flags": "S"}, 
                    {'payload': 'goodbye', 'From' : 'afoe', "flags": "F" })
        request.context = {}
        for i in range(len(messages)):
            request.context[i] = MboxMessage(messages[i]['payload'])
            request.context[i]['From'] = messages[i]['From']
            request.context[i].set_flags(messages[i]['flags'])
        
        input =  {"0": messages[0], 
                  "1": messages[1]}
        input['0']['date'] = request.context[0].get_date()
        input['1']['date'] = request.context[1].get_date()    
        
        response = self._callFUT(request.context, request)
        self.assertEqual(response.headerlist[0],
                         ('Content-Type', 'application/x-json'))
        json_payload = response.app_iter[0]
        self.assertEqual(json_payload, '{}')
        self.assertEqual(request.context[1].get_flags(), 'FS')
 
    def zztest_modify_queue_error(self):                 
        from opencore.utilities.message import MboxMessage 
        import simplejson as json
        request = testing.DummyRequest(path='/mailbox/johnny', post={99 : {'flags' : 'FS'}})
        messages = ({'payload' :'hello', 'From' : 'niceguy', "flags": "S"}, 
                    {'payload': 'goodbye', 'From' : 'afoe', "flags": "F" })
        request.context = {}
        for i in range(len(messages)):
            request.context[i] = MboxMessage(messages[i]['payload'])
            request.context[i]['From'] = messages[i]['From']
            request.context[i].set_flags(messages[i]['flags'])
        
        input =  {"0": messages[0], 
                  "1": messages[1]}
        input['0']['date'] = request.context[0].get_date()
        input['1']['date'] = request.context[1].get_date()    
        
        response = self._callFUT(request.context, request)
        self.assertEqual(response.headerlist[0],
                         ('Content-Type', 'application/x-json'))
        json_payload = response.app_iter[0]
        self.assertTrue(json.loads(json_payload).has_key('Error'))

    def zztest_evolve2_root_mailbox_exists(self):
        root, _ = open_root(get_default_config())
        
        self.assertTrue('mailboxes' in root['site'])
        self.assertTrue(isinstance(root['site']['mailboxes'], Folder))
        
    def test_x(self):
        site, _ = open_root(get_default_config())
        
        mbt = MailboxTool()
        now = str(datetime.utcnow())

        from_ = 'admin'
        to = ['joe', 'sarah']

        subject = 'Hi there'
        payload = 'payload'
        flags = ['read']
        
        thread_id = 'openhcd.' + uuid.uuid4().hex
        msg_id = 'openhcd.' +  now + '.' + uuid.uuid4().hex
        
        msg = MboxMessage(payload)
        msg['Message-Id'] = msg_id
        msg['Subject'] = subject
        msg['From'] = from_
        msg['To'] = ', '.join(to)
        msg['Date'] = now
        msg['X-oc-thread-id'] = thread_id
        
        mbt.send_message(site, from_, to, msg)
        mbt.delete_message(site, from_, 'sent', thread_id, msg_id)
        
        mbt.send_message(site, from_, to, msg)
        mbt.set_message_flags(site, from_, 'sent', thread_id, msg_id, flags)
        
        raw_msg, msg = mbt.get_message(site, from_, 'sent', thread_id, msg_id)
        
        queues = mbt.get_queues(site, from_, 'sent')
        #print(queues)
'''
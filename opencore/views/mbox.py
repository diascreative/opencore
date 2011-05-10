from repoze.bfg.view import bfg_view
from repoze.bfg.url import model_url
from webob.exc import HTTPFound
from webob import Response
from repoze.bfg.view import render_view_to_response
from simplejson import JSONEncoder, loads
from opencore.utilities.mbox import Queue
from opencore.views.api import TemplateAPI
import logging
from opencore.utils import compact_traceback

log = logging.getLogger(__name__)

class MboxView(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
         
    def __call__(self):
        context, request = self.context, self.request
        api = TemplateAPI(context, request)
        return self.queue_view(context, request)

    def queue_view(self, context, request): 
        """
        GET requests return the contents of a users message box as a json dict
        i.e. /mailbox/nick hork 
        
        "0": {"From": "zyf  | OPEN IDEO <notifications@openideo.com>", 
              "flags": "", 
              "date": 1290932490.875488, 
              "from": "notifications@openideo.com", 
              "Subject": "[How can we raise kids' awareness of the benefits of fresh food so\n\tthey can make better choices?] Re: Do It Yourself Family Dining\n\tExperience - At a Restaurant", 
              "Content-Type": "text/html; charset=\"utf-8\"", 
              "payload": "<html>...</html>"},
        "1": {...}       
      
             
        PUT posts can change the message flags:
        F (Flagged) marked as important
        S (Seen) Read
        T (Trashed) marked for subsequent deletion
        
        Flag states can be concatenated together in alphabetical order.
        i.e.
       
        PUT /mailbox/john  
       
        {1: {"flags": "FS"}}
        """
        try:
            status = {}
            q = context
            if request.method == 'POST':
                changed_messages = request.POST
                for msgid in changed_messages.keys():
                    msg = q.get(msgid)
                    if not msg:
                        raise ValueError('No msgid: %d found in queue: %s' % 
                                         (msgid, request.path))
                    msg.set_flags(changed_messages[msgid]['flags'])
            else:
                messages = {}
                ignore_email_headers = ('Content-Transfer-Encoding', 
                  'Reply-to', 'To', 'MIME-Version', 'Message-Id')
                for i in range(len(q)):
                    msg = q.get(i)
                    msg_data = dict(zip(msg.keys(), msg.values()))
                    for item in ignore_email_headers:
                        if item in msg_data:
                            del msg_data[item]
                    msg_data['flags'] = msg.get_flags()
                    msg_data['payload'] = msg.get_payload(decode=True)
                    msg_data['date'] = msg.get_date()
                    messages[i] = msg_data
                result = JSONEncoder().encode(messages)
                return Response(result, content_type="application/x-json")    
           
        except Exception, err:
            nil, t, v, tbinfo = compact_traceback()
            err_msg = 'mbox view error: (%s:%s %s)' % (t, v, tbinfo)
            log.error(err_msg) 
            status['Error'] = err_msg
           
        return Response(JSONEncoder().encode(status), content_type="application/x-json") 

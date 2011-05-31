
# stdlib
import time
import logging
import email.generator
import email.parser
from datetime import datetime
from uuid import uuid4

# Zope
import transaction

# Repoze
from repoze.folder import Folder
from repoze.bfg.security import Allow

# Zope
from BTrees.IOBTree import IOBTree
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from ZODB.blob import Blob

# opencore
from opencore.models.mbox import STATUS_READ
from opencore.security.policy import ADMINISTRATOR_PERMS
from opencore.security.policy import MEMBER_PERMS
from opencore.security.policy import NO_INHERIT
from opencore.utilities.message import MboxMessage


"""
User messages are stored in mailboxes mounted in ZODB at root['site']['mailboxes']. When a user
is being created, it's assigned two mailboxes, 'inbox' and 'sent' whose paths
follow the pattern of

root['site']['mailboxes']['username.inbox']
root['site']['mailboxes']['username.sent']

Each mailbox uses a QueuesFolder for storing the list of message queues. Each
message queue is a sort of a conversation akin to what most MUAs (like Thunderbird
or Apple Mail) call a message thread, the difference being that opencore's
messages queues are always linear, there's no tree view over the whole queue.
Each message queue consists of at least one message. The name of the message
queue is taken from the first message that's added to the queue however the name
is not used for uniquely identifying queue because there can be many queues
sharing the same name (the same message subject, that is), thus a thread ID is
used for identifying the Queue objects.

ASCII art below depicts relations between the classes.

root['site']['mailboxes']['username.inbox'] (a QueuesFolder)
   |
   -----------------------> Queue 0 "How was the meeting"
   |                          |
   |                          |--> Message 0 "How was the meeting"
   |                          |--> Message 1 "Re: How was the meeting"
   |                          |--> Message 2 "Re: How was the meeting"
   |                           
   -----------------------> (other Queues)
"""

log = logging.getLogger(__name__)

def _new_id(container):
    """ Use numeric incrementally increasing ids to preserve FIFO order.
    """
    if len(container):
        return max((int(elem) for elem in container.keys())) + 1
    return 0

def _get_mailbox(site, profile_name, suffix):
    return site['mailboxes'][profile_name + '.' + suffix]

class MBoxException(Exception):
    def __init__(self, msg):
        self.msg = msg

class NoSuchThreadException(MBoxException):
    """ Raised when an attempt to find a a thread fails.
    """
    
class NoSuchMessageException(MBoxException):
    """ Raised when an attempt to find a a message fails.
    """

class _NullLog(object):
    def info(self, *args): pass
    def warn(self, *args): pass
    def error(self, *args): pass

class QueuesFolder(Folder):
    """ Container for mailbox queues.
    """

class QueueIterator(object):
    
    def __init__(self, queue):
        self.q = queue
        self.iter = iter([int(elem) for elem in self.q._messages.keys()])
      
    def next(self):
        """ Retrieve the next message in the queue.
        """
        key = self.iter.next()
        message = self.q._messages.get(int(key))
        return message.get()
           

class Queue(Persistent):
    """ Implements a first in first out (FIFO) message queue.
    """
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self._messages = IOBTree()
        
    def add(self, message):
        """ Add a message to the queue.
        """
        try:
            message = _QueuedMessage(message)
            id = _new_id(self._messages)
            self._messages[id] = message
        except:
            transaction.abort()
            raise
        else:
            transaction.commit()
            
    def delete_message(self, message_id):
        """ Deletes a message by its Message-Id header.
        """
        for msg_no, msg in self._messages.items():
            if msg.message_id == message_id:
                del self._messages[msg_no]
                break
        else:
            msg = 'Could not find message [%s]' % message_id
            raise NoSuchMessageException(msg)

    def pop_next(self):
        """ Retrieve the next message in the queue, removing it from the queue.
        """
        key = iter(self._messages.keys()).next()
        message = self._messages.pop(key)
        return message.get()
    
    def get(self, index):
        """ Retrieve the message at the specified index. The index starts from 0.
        """ 
        message = self._messages[index]
        return message.get()
         
    def __iter__(self):   
        return QueueIterator(self)  
    
    def __len__(self):
        return self._messages.__len__()

    def __getitem__(self, ind):
        return self.get(ind)
    
    def __repr__(self):
        return '<%s at %s, id=[%s], name=[%s]>' % (self.__class__.__name__,
            hex(id(self)), self.id, self.name)
   
  
class _QueuedMessage(Persistent):
    """ Wrapper for storing email messages in queues.  Stores email as flattened
    bytes in a blob.
    """
    _v_message = None  # memcache message once loaded

    def __init__(self, message, flags=[]):
        if not isinstance(message, MboxMessage):
            raise ValueError("Not a MboxMessage message. found type=%s" % \
                             message.__class__.__name__)

        self.message_id = message['Message-Id']
        self.flags = flags
        
        self._v_message = message   # transient attribute
        self._blob_file = blob = Blob()
        outfp = blob.open('w')
        email.generator.Generator(outfp).flatten(message)
        outfp.close()

    def get(self):
        if self._v_message is None:
            parser = email.parser.Parser(MboxMessage)
            self._v_message = parser.parse(self._blob_file.open())
        return self._v_message

class MailboxTool(object):
    """ A general purpose utility class for the management of user messages.
    """

    # Overridable for testing
    Queue = Queue

    @staticmethod
    def _new_id(prefix):
        return prefix + '.' + str(datetime.utcnow()) + '.' + uuid4().hex
    
    @staticmethod
    def new_message_id():
        return MailboxTool._new_id('msg_id')
    
    @staticmethod
    def new_thread_id():
        return MailboxTool._new_id('thread_id')
    
    def _create_add_queue_message(self, mbox, profile_name, message):
        """ Adds a message to a queue. The queue is created as neccessary
        if it doesn't exist yet.
        """
        thread_id = message['X-oc-thread-id']
        
        for q_no in mbox:
            q = mbox.get(q_no)
            if q.id == thread_id:
                # Found the queue.
                q.add(message)
                break
        else:
            # Need a new queue.
            new_q_id = _new_id(mbox)
            new_q = Queue(thread_id, message['Subject'])
            self.set_acl(profile_name, new_q)
            new_q.add(message)
            mbox[str(new_q_id)] = new_q
            
    def _get_mailbox_queue_message(self, site, profile_name, mbox_type, thread_id, message_id,
                                   fetch_inner_message=False):
        """ Returns a 5-element tuple of (mailbox, queue, queue number, raw message,
        actual message), based on the input parameters.
        """
        inner_message = None
        q, mb, q_no = self.get_queue_data(site, profile_name, mbox_type, thread_id)
        
        for msg_no in q._messages:
            raw_msg = q._messages.get(int(msg_no))
            if raw_msg.message_id == message_id:
                if fetch_inner_message:
                    inner_message = raw_msg.get()
                break
        else:
            error = 'Could not find message [%s], thread [%s], profile [%s], mbox [%s]' % (
                message_id, thread_id, profile_name, mbox_type)
            raise NoSuchMessageException(error)
        
        return mb, q, q_no, raw_msg, inner_message
    
    def set_acl(self, name, queue):
        """ Sets the appropriate permissions on the queue object.
        """
        acl = []
        acl.append((Allow, 'group.KarlAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, 'group.KarlUserAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, name, MEMBER_PERMS))
        acl.append(NO_INHERIT)
        queue.__acl__ = acl
        
    def get_mailbox(self, parent, path):
        """ Gets a user's mailbox. The mailbox is created if it doesn't exist
        already.
        """
        self.path = path.strip('/').split('/')
        for name in self.path[:-1]:
            parent = parent[name]
        name = self.path[-1]
        try:
            folder = parent.get(name)
            if folder is None:
                folder = QueuesFolder()
                parent[name] = folder
                log.info('creating new mailbox %s' %  name)
        except:
            transaction.abort()
            raise
        else:
            transaction.commit()
            return folder
        
    def get_queues(self, site, profile_name, mbox_type):
        queues = []
        mb = _get_mailbox(site, profile_name, mbox_type)
        
        q_numbers = (int(elem) for elem in mb)
        
        for q_no in reversed(sorted(q_numbers)):
            queues.append(mb[q_no])
            
        return queues
    
    def get_queue_data(self, site, profile_name, mbox_type, thread_id):
        mb = _get_mailbox(site, profile_name, mbox_type)
        for q_no in mb:
            q = mb.get(q_no)
            if q.id == thread_id:
                break
        else:
            error = 'Could not find thread [%s], profile [%s], mbox [%s]' % (
                thread_id, profile_name, mbox_type)
            raise NoSuchThreadException(error)
        
        return q, mb, q_no
        
        
    def send_message(self, site, from_, to, message, should_commit=False):
        """ Sends a message. Creates 'sent' and 'inbox' queues where appropriate.
        """
        
        # Is it a new thread from the sender's perspective? Add a new 'sent'
        # queue if so. In other case, append the message to an already existing
        # 'sent' queue..
        sent_mb = _get_mailbox(site, from_, 'sent')
        self._create_add_queue_message(sent_mb, from_, message)
        
        # ..same goes for recipients and their 'inbox' queues.
        inbox_mb = _get_mailbox(site, to.__name__, 'inbox')
        self._create_add_queue_message(inbox_mb, to.__name__, message)
        
        if should_commit:
            transaction.commit()
        
    def delete_message(self, site, profile_name, mbox_type, thread_id, message_id):
        """ Deletes a message. If it was the only message in a queue, the queue
        is also deleted.
        """

        # Fetch the needed objects
        mb, q, q_no, raw_msg, msg = self._get_mailbox_queue_message(site, profile_name, 
                                    mbox_type, thread_id, message_id)

        # Will we have to delete the queue as well once the message has been?
        should_delete_q = len(q) == 1
        
        q.delete_message(message_id)
        
        if should_delete_q:
            del mb[q_no]
            
    def delete_thread(self, site, profile_name, mbox_type, thread_id):
        """ Deletes a whole message thread.
        """
        mbox = sent_mb = _get_mailbox(site, profile_name, mbox_type)
        for q_no in mbox:
            q = mbox.get(q_no)
            if q.id == thread_id:
                del mbox[q_no]
                break
        else:
            error = 'Could not find thread [%s], profile [%s], mbox [%s]' % (
                thread_id, profile_name, mbox_type)
            raise NoSuchThreadException(error)
        
            
    def set_message_flags(self, site, profile_name, mbox_type, thread_id, message_id, flags):
        """ Sets the message's flags.
        """
        # Fetch the needed object
        _, _, _, raw_msg, _ = self._get_mailbox_queue_message(site, profile_name, 
                                    mbox_type, thread_id, message_id)
        raw_msg.flags = flags
        
    def get_message(self, site, profile_name, mbox_type, thread_id, message_id):
        """ Return a pair of raw_msg, msg based no the input criteria. 'raw_msg'
        is a _QueueMessage instance, 'msg' is an MboxMessage.
        """
        # Fetch the needed objects
        _, _, _, raw_msg, msg = self._get_mailbox_queue_message(site, profile_name, 
                                    mbox_type, thread_id, message_id, True)
        
        return raw_msg, msg
    
    def get_unread(self, site, profile_name, mbox_type='inbox'):
        """ Returns the number of unread messages in the user's mbox of a given
        type.
        """
        total = 0
        
        mbox_queues = self.get_queues(site, profile_name, mbox_type)
        for mbox_q in mbox_queues:
            for msg_no in mbox_q._messages:
                raw_msg = mbox_q._messages[msg_no]
                if not STATUS_READ in raw_msg.flags:
                    total += 1
                    
        return total
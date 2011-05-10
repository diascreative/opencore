
# stdlib
import time
import transaction
import logging
import email.generator
import email.parser

# Repoze
from repoze.folder import Folder
from repoze.bfg.security import Allow

# Zope
from BTrees.IOBTree import IOBTree
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from ZODB.blob import Blob

# opencore
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
sharing the same name (the same message 

ASCII art below depicts relations between the classes.

root['site']['mailboxes']['username.inbox']
   |
   | (uses QueuesFolder)
   -----------------------> Queue "How was the meeting"
   |                          |
   |                          |--> Message "How was the meeting"
   |                          |--> Message "All good, no decisions though"
   |                          |--> Message "I see, too bad"
   |                           
   -----------------------> (other Queues)
"""

log = logging.getLogger(__name__)

def _new_id(container):
    # Use numeric incrementally increasing ids to preserve FIFO order
    if len(container):
        return max((long(elem) for elem in container.keys())) + 1
    return 0

def _get_mailbox(site, profile_name, suffix):
    return site['mailboxes'][profile_name + '.' + suffix]

class _NullLog(object):
    def info(self, *args): pass
    def warn(self, *args): pass
    def error(self, *args): pass


class QueuesFolder(Folder):
    """
    Container for mailbox queues.
    """

class QueueIterator(object):
    
    def __init__(self, queue):
        self.q = queue
        self.iter = iter([long(elem) for elem in self.q._messages.keys()])
      
    def next(self):
        """
        Retrieve the next message in the queue.
        """
        key = self.iter.next()
        message = self.q._messages.get(key)
        return message.get()
           

class Queue(Persistent):
    """
    Implements a first in first out (FIFO) message queue.
    """
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self._messages = IOBTree()
        self._message_ids = OOBTree()
        
    def add(self, message):
        """
        Add a message to the queue.
        """
        try:
            id = message['Message-Id']
            if not id:
                id = message['Message-Id'] = email.utils.make_msgid()    
            self._message_ids[message['Message-Id']] = time.time()
            message = _QueuedMessage(message)
            id = _new_id(self._messages)
            self._messages[id] = message
        except:
            transaction.abort()
            raise
        else:
            transaction.commit()

    def is_duplicate(self, message):
        try:
            message_ids = self._message_ids
        except AttributeError:
            # BBB persistence
            self._message_ids = message_ids = OOBTree()
            return False
      
        return message['Message-Id'] in message_ids

    def pop_next(self):
        """
        Retrieve the next message in the queue, removing it from the queue.
        """
        key = iter(self._messages.keys()).next()
        message = self._messages.pop(key)
        return message.get()
    
    def get(self, index):
        """
        Retrieve the message at the specified index. The index starts from 0.
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
    """
    Wrapper for storing email messages in queues.  Stores email as flattened
    bytes in a blob.
    """
    _v_message = None  # memcache message once loaded

    def __init__(self, message):
        if not isinstance(message, MboxMessage):
            raise ValueError("Not a MboxMessage message. found type=%s" % \
                             message.__class__.__name__)
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
    """ FIXME: Update the docstring
    Mailbox is a zodb persistent container for users messages. The path to the mailbox is
    configurable which enables the mailboxs to be located anywhere in the zodb tree and 
    supports having multiple mailboxs in the tree. The default location is '/mailbox'.
    A repoze.folder is used for the QueuesFolder to provide instance level security.  
    """

    # Overridable for testing
    Queue = Queue
        
    @staticmethod    
    def open_queue(root, user, path='mailbox'):
        path = path.strip('/').split('/')
        for name in path[:-1]:
            root = root[name]
        name = path[-1]
        mailbox = root.get(name)
        if mailbox:
            try:
                return mailbox[user]
            except:
                raise KeyError("No '%s' user found under mailbox folder" % user) 
        else:
            raise KeyError("No '%s' mailbox folder found under root" % name)
                            
    def get_mailbox(self, parent, path):
        """ Gets the root mailbox object, an instance of `QueuesFolder`.  
        If folder does not exist it is created.  Its parent, however, 
        must already exist if a nested zodb_path is used.
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
        
    def set_acl(self, name, queue):
        """ Sets the appropriate permissions on the queue object.
        """
        acl = []
        acl.append((Allow, 'group.KarlAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, 'group.KarlUserAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, name, MEMBER_PERMS))
        acl.append(NO_INHERIT)
        queue.__acl__ = acl
        
    def _create_add_queue_message(self, mbox, profile_name, message):
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
        
    def send_message(self, site, from_, to, message):
        
        # Is it a new thread from the sender's perspective? Add a new 'sent'
        # queue if so. In other case, append the message to an already existing
        # 'sent' queue..
        sent_mb = _get_mailbox(site, from_, 'sent')
        self._create_add_queue_message(sent_mb, from_, message)
        
        # ..same goes for recipients and their 'inbox' queues.
        for profile_name in to:
            inbox_mb = _get_mailbox(site, profile_name, 'inbox')
            self._create_add_queue_message(inbox_mb, profile_name, message)
        
        transaction.commit()
        
    def set_acl(self, name, queue):
        acl = []
        acl.append((Allow, 'group.KarlAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, 'group.KarlUserAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, name, MEMBER_PERMS))
        acl.append(NO_INHERIT)
        queue.__acl__ = acl 
        
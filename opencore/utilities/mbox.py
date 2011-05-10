from BTrees.IOBTree import IOBTree
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from ZODB.blob import Blob
from repoze.folder import Folder
from repoze.bfg.security import Allow

import email.generator
import email.parser
from opencore.security.policy import ADMINISTRATOR_PERMS
from opencore.security.policy import MEMBER_PERMS
from opencore.security.policy import NO_INHERIT
from opencore.utilities.message import MboxMessage

import time
import transaction
import logging

log = logging.getLogger(__name__)

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
        self.iter = iter(self.q._messages.keys())
      
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
    def __init__(self):
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



class Mailbox(object):
    """
    Mailbox is a zodb persistent container for users messages. The path to the mailbox is
    configurable which enables the mailboxs to be located anywhere in the zodb tree and 
    supports having multiple mailboxs in the tree. The default location is '/mailbox'.
    A repoze.folder is used for the QueuesFolder to provide instance level security.  
    """

    # Overridable for testing
    Queue = Queue

    def __init__(self, users, root, path='mailbox'):
        """
        Initialize from a list of provided users.
        """
        self.mailbox = self._get_mailbox(root, path)
        self._init_queues(users)
        
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
                            

    """
    Gets the root mailbox object, an instance of `QueuesFolder`.  
    If folder does not exist it is created.  It's parent, however, 
    must already exist if a nested zodb_path is used.
    """
    def _get_mailbox(self, parent, path):
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
        
    def _init_queue(selfself, user):
        # to be extended 
        return dict(name=user)
          
    def _init_queues(self, users):
        queues = []
        for user in sorted(users):
            queues.append(self._init_queue(user))
        self.configured_queues = queues    
        self.reconcile_queues(log=log)
        
    def set_acl(self, name, queue):
        acl = []
        acl.append((Allow, 'group.KarlAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, 'group.KarlUserAdmin', ADMINISTRATOR_PERMS))
        acl.append((Allow, name, MEMBER_PERMS))
        acl.append(NO_INHERIT)
        queue.__acl__ = acl 
            
    def reconcile_queues(self, log=None):
        """
        Reconciles users with queues in database. If new users have been 
        added, those user queues are added to the database.  If old users 
        have been removed, they are removed from the database.
        """
        if log == None:
            log = _NullLog()

        # Reconcile configured queues with queues in db
        configured = self.configured_queues
        try:
            # Create new queues
            for queue in configured:
                name = queue['name']
                if name not in self.mailbox:
                    self.mailbox[name] = self.Queue()
                    self.set_acl(name, self.mailbox[name])
                    log.info('Created new mailbox queue: %s' % name)
    
            # Remove old queues 
            configured_names = set([q['name'] for q in configured])
            for name in set(self.mailbox.keys()):
                if name not in configured_names:
                    log.info('Removed old mailbox queue: %s' % name)
                    del self.mailbox[name]         
        except:
            transaction.abort()
            raise
        else:
            transaction.commit()
                           

def _new_id(container):
    # Use numeric incrementally increasing ids to preserve FIFO order
    if len(container):
        return max(container.keys()) + 1
    return 0

      

import logging
from zope.interface import implements
from persistent import Persistent
from appendonly import AppendStack
from opencore.models.interfaces import ILike

log = logging.getLogger(__name__)

class Like(Persistent):
    '''
    Like content. 
    '''
    implements(ILike)
    
    def __init__(self, user=None):
        self.users = AppendStack()
        self._count = 0
        if user:
            self.users.push(user)
            self._count += 1
        
    def __len__(self):
        return len(list(self.users))
    
    def count(self):
        return self._count 
    
    def add(self, user):  
        self.users.push(user)
        self._count += 1
        
    def has_user(self, user): 
        for x,y,u in self.users:
            log.debug('%s=%s' % (user, u))
            if user == u:
                return True  
        return False    
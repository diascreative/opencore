
# stdlib
from datetime import datetime, timedelta

# Zope
from zope.interface import implements

# opencore
from opencore.models.interfaces import IPasswordRequestRequest

REQUEST_VALIDITY_HOURS = 24

class PasswordRequestRequest(object):
    implements(IPasswordRequestRequest)
    
    def __init__(self, request_id, email):
        self.request_id = request_id
        self.email = email
        self.valid_from, self.valid_to = self.get_valid_from_to()
        
    def get_valid_from_to(self):
        from_ = datetime.utcnow()
        to = from_ + timedelta(hours=REQUEST_VALIDITY_HOURS)
        return from_, to
    
    def __repr__(self):
        return '<%s at %s, request_id=[%s] valid_from=[%s] valid_to=[%s]>' % (
            self.__class__.__name__, hex(id(self)), self.request_id, 
            self.valid_from, self.valid_to)
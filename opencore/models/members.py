"""A folder that manages community membership.

A community will have a sub-item of `members` that can be traversed
to.  It will then have views registered against it for the various
screens, and methods that provide easy access to data stored outside
of the folder (e.g. current members.) It will also contain some
persistent content, such as invitations.
"""

from zope.interface import implements
from repoze.folder import Folder
from persistent import Persistent

from opencore.models.interfaces import IMembers
from opencore.models.interfaces import IInvitation

class Invitation(Persistent):
    implements(IInvitation)

    def __init__(self, email, message):
        Persistent.__init__(self)
        self.email = unicode(email)
        self.message = unicode(message)
        
class Members(Folder):
    implements(IMembers)


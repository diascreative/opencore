
""" An attachments facility that can be hung off resources"""

from zope.interface import implements
from repoze.folder import Folder

from opencore.models.interfaces import IAttachmentsFolder

class AttachmentsFolder(Folder):
    implements(IAttachmentsFolder)
    title = u'Attachments Folder'

    #XXX next_id appears to be unused--attachment ids are filenames of
    #    uploaded files.
    @property
    def next_id(self):
        """Return a string with the next highest number key"""
        try:
            maxkey = self.data.maxKey()
        except ValueError:
            # no members
            return '1'
        return unicode(int(maxkey) + 1)
    

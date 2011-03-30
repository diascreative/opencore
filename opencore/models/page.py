
from zope.interface import implements

from repoze.folder import Folder

from opencore.models.interfaces import IPage
from opencore.models.attachments import AttachmentsFolder

class Page(Folder):
    implements(IPage)
    modified_by = None

    def __init__(self, title, text, description, creator):
        Folder.__init__(self)
        assert title is not None
        assert text is not None
        assert description is not None
        assert creator is not None
        self.title = unicode(title)
        self.text = unicode(text)
        self.description = unicode(description)
        self.creator = unicode(creator)
        self.modified_by = self.creator
        # We might choose to make this more article-ish in KARL3
        self['attachments'] = AttachmentsFolder()

# No tool factory because these are stored in folders

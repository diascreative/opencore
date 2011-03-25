from zope.interface import implements

from repoze.lemonade.content import create_content
from repoze.folder import Folder

from opencore.models.interfaces import IToolFactory
from opencore.models.tool import ToolFactory

from opencore.models.interfaces import IBlog
from opencore.models.interfaces import IBlogEntry

from opencore.models.commenting import CommentsFolder
from opencore.models.attachments import AttachmentsFolder

class Blog(Folder):
    implements(IBlog)
    title = u'Blog'

class BlogEntry(Folder):
    implements(IBlogEntry)
    modified_by = None

    def __init__(self, title, text, description, creator):
        super(BlogEntry, self).__init__()
        assert title is not None
        assert text is not None
        assert description is not None
        assert creator is not None
        self.title = unicode(title)
        self.text = unicode(text)
        self.description = unicode(description)
        self.creator = unicode(creator)
        self.modified_by = self.creator
        self['comments'] = CommentsFolder()
        self['attachments'] = AttachmentsFolder()

    def get_attachments(self):
        return self['attachments']

class BlogToolFactory(ToolFactory):
    implements(IToolFactory)
    name = 'blog'
    interfaces = (IBlog, IBlogEntry)
    def add(self, context, request):
        blog = create_content(IBlog)
        context['blog'] = blog

    def remove(self, context, request):
        del context['blog']

blog_tool_factory = BlogToolFactory()
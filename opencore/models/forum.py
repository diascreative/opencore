from zope.interface import implements

from repoze.lemonade.content import create_content
from repoze.folder import Folder

from opencore.models.interfaces import IToolFactory
from opencore.models.tool import ToolFactory

from opencore.models.interfaces import IForum
from opencore.models.interfaces import IForumTopic
from opencore.models.interfaces import IForumsFolder

from opencore.models.commenting import CommentsFolder
from opencore.models.attachments import AttachmentsFolder

class ForumsFolder(Folder):
    implements(IForumsFolder)
    title = u'Forums'

class Forum(Folder):
    implements(IForum)
    modified_by = None

    def __init__(self, title, description='', creator=None):
        super(Forum, self).__init__()
        self.title = unicode(title)
        self.description = unicode(description)
        self.creator = unicode(creator)
        self.modified_by = self.creator

class ForumTopic(Folder):
    implements(IForumTopic)
    modified_by = None

    def __init__(self, title='', text='', creator=None):
        super(ForumTopic, self).__init__()
        self.title = unicode(title)
        if text is None:
            self.text = u''
        else:
            self.text = unicode(text)
        self.creator = unicode(creator)
        self.modified_by = self.creator
        self['comments'] = CommentsFolder()
        self['attachments'] = AttachmentsFolder()

class ForumsToolFactory(ToolFactory):
    implements(IToolFactory)
    name = 'forums'
    interfaces = (IForumsFolder, IForum, IForumTopic)
    def add(self, context, request):
        forums = create_content(IForumsFolder)
        context['forums'] = forums

    def remove(self, context, request):
        del context['forums']

forums_tool_factory = ForumsToolFactory()

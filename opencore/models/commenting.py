""" A commenting facility that can be hung off resources"""

from zope.interface import implements
from repoze.folder import Folder

from opencore.models.interfaces import ICommentsFolder
from opencore.models.interfaces import IComment

class CommentsFolder(Folder):
    implements(ICommentsFolder)
    title = u'Comments Folder'

    @property
    def next_id(self):
        """Return a string with the next highest number key"""
        try:
            maxkey = self.data.maxKey()
        except ValueError:
            # no members
            return u'001'
        return u"%03d" % (int(maxkey) + 1)

class Comment(Folder):
    """ A comment can contain attachments """

    implements(IComment)
    attachments = None
    modified_by = None

    # XXX: description is probalby not needed--not sure when that would show
    #      up in UI.
    def __init__(self, title, text, description, creator):
        super(Comment, self).__init__()
        self.title = unicode(title)
        if text is None:
            self.text = u''
        else:
            self.text = unicode(text)
        if description is None:
            self.description = u''
        else:
            self.description = unicode(description)
        self.creator = unicode(creator)
        self.modified_by = self.creator

    def get_attachments(self):
        return self
    
    def is_reply(self):
        return IComment.providedBy(self.__parent__.__parent__)
    
    def comment_for_reply(self):
        comment = None
        if self.is_reply():
            comment = self.__parent__.__parent__
        return comment    
    
    def has_replies(self):
        _has_replies = False
        if self.replies():
            _has_replies = True
        return _has_replies
    
    def replies(self):
        return self.get('comments')    

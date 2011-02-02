from zope.interface import implements
from repoze.folder import Folder

from opencore.interfaces import ICommunity
from opencore.interfaces import ICommunities
from opencore.members import Members

from opencore.utils import find_users

class Community(Folder):
    implements(ICommunity)
    _members_group = 'group.community:%s:members'
    _moderators_group = 'group.community:%s:moderators'
    default_tool = '' # means default tab (overview)
    content_modified = None # will be set by subscriber
    modified_by = None

    def __init__(self, title, description, text=u'', creator=u''):

        super(Community, self).__init__()
        self.title = unicode(title)
        self.description = unicode(description)
        if text is None:
            self.text = u''
        else:
            self.text = unicode(text)            
        self.creator = self.modified_by = creator
        self['members'] = members = Members()

    @property
    def members_group_name(self):
        return self._members_group % self.__name__

    @property
    def moderators_group_name(self):
        return self._moderators_group % self.__name__

    @property
    def number_of_members(self):
        return len(self.member_names)

    @property
    def member_names(self):
        name = self._members_group % self.__name__
        return self._get_group_names(name)

    @property
    def moderator_names(self):
        name = self._moderators_group % self.__name__
        return self._get_group_names(name)

    def _get_group_names(self, group):
        users = find_users(self)
        names = users.users_in_group(group)
        return set(names)
        

class CommunitiesFolder(Folder):
    implements(ICommunities)
    title = 'Communities'

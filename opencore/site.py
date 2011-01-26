import datetime

from BTrees.OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from repoze.bfg.interfaces import ILocation
from repoze.bfg.security import Allow
from repoze.bfg.security import Authenticated
from repoze.bfg.security import principals_allowed_by_permission
from repoze.bfg.traversal import model_path
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.path2 import CatalogPathIndex2
from repoze.catalog.document import DocumentMap
from repoze.folder import Folder
from repoze.lemonade.content import create_content
from repoze.lemonade.content import IContent
from repoze.session.manager import SessionDataManager
from repoze.who.plugins.zodb.users import Users
from zope.interface import implements
from zope.interface import providedBy
from zope.interface.declarations import Declaration
from zope.component import getUtilitiesFor
from zope.component import queryAdapter
from zope.event import notify

from opencore.catalog import CachingCatalog
from opencore.interfaces import ICommunities
from opencore.interfaces import IIndexFactory
from opencore.interfaces import IProfile
from opencore.interfaces import IProfiles
from opencore.interfaces import ISite
from opencore.interfaces import ITextIndexData

from opencore.interfaces import IVirtualData
from opencore.interfaces import IUserAdded
from opencore.interfaces import IUserAddedGroup
from opencore.interfaces import IUserRemoved
from opencore.interfaces import IUserRemovedGroup
from opencore.tagging import Tags
from opencore.tagging.index import TagIndex
from opencore.utils import coarse_datetime_repr

class UserEvent(object):
    def __init__(self, site, id, login, groups, old_groups=None):
        self.site = site
        self.id = id
        self.login = login
        self.groups = groups
        self.old_groups = old_groups

class UserAddedEvent(UserEvent):
    implements(IUserAdded)

class UserRemovedEvent(UserEvent):
    implements(IUserRemoved)

class UserAddedGroupEvent(UserEvent):
    implements(IUserAddedGroup)

class UserRemovedGroupEvent(UserEvent):
    implements(IUserRemovedGroup)

class KARLUsers(Users):

    def __init__(self, site):
        super(KARLUsers, self).__init__()
        self.site = site

    def add(self, id, login, password, groups=None, encrypted=False):
        super(KARLUsers, self).add(id, login, password, groups,
                                   encrypted=encrypted)
        notify(UserAddedEvent(self.site, id, login, groups))

    def remove(self, id):
        info = self.byid[id] # XXX should be self.data
        super(KARLUsers, self).remove(id)
        notify(UserRemovedEvent(self.site, id, info['login'], info['groups']))

    def add_group(self, id, group):
        info = self.byid[id] # XXX should be self.data
        before = set(info['groups'])
        super(KARLUsers, self).add_group(id, group)
        after = set(info['groups'])
        if before != after:
            notify(UserAddedGroupEvent(self.site, id, info['login'],
                                       after, before))

    def remove_group(self, id, group):
        info = self.byid[id] # should be self.data
        before = set(info['groups'])
        super(KARLUsers, self).remove_group(id, group)
        after = set(info['groups'])
        if before != after:
            notify(UserRemovedGroupEvent(self.site, id, info['login'],
                                         after, before))


def get_acl(object, default):
    return getattr(object, '__acl__', default)

def get_title(object, default):
    title = getattr(object, 'title', '')
    if isinstance(title, basestring):
        # lowercase for alphabetic sorting
        title = title.lower()
    return title

def get_name(object, default):
    return getattr(object, '__name__', default)

def get_title_firstletter(object, default):
    title = get_title(object, default)
    if title:
        try:
            title = title[0]
        except TypeError:
            return default
        try:
            return title.upper()
        except AttributeError:
            return default
    return default

def get_interfaces(object, default):
    # we unwind all derived and immediate interfaces using spec.flattened()
    # (providedBy would just give us the immediate interfaces)
    provided_by = list(providedBy(object))
    spec = Declaration(provided_by)
    ifaces = list(spec.flattened())
    return ifaces

def get_path(object, default):
    return model_path(object)

def get_textrepr(object, default):
    adapter = queryAdapter(object, ITextIndexData)
    if adapter is not None:
        text = adapter()
        return text
    elif (IContent.providedBy(object)):
        fmt = "%s %s"
        tr = fmt % (
            getattr(object, 'title', ''),
            getattr(object, 'description', ''),
            )
        return tr
    return default

def get_weighted_textrepr(object, default):
    # For use with experimental pgtextindex, which uses a list of strings,
    # in descending order by weight.

    # The so called 'standard' repr already has a weight of sorts applied to
    # it, accomplished by repeating the elements that are supposed to be more
    # heavily weighted.  For the purposes of supporting both types of text
    # indexes, this double weighting is fine.
    standard_repr = get_textrepr(object, default)

    # If we wouldn't normally index it, then we can stop now
    if standard_repr is default:
        return default

    # Weight title most, description second, then whatever get_textrepr returns
    reprs = []
    for attr in ('title', 'description'):
        value = getattr(object, attr, '')
        if not isinstance(value, basestring):
            value = ''
        reprs.append(value)
    reprs.append(standard_repr)

    return reprs

def _get_date_or_datetime(object, attr, default):
    d = getattr(object, attr, None)
    if (isinstance(d, datetime.datetime) or
        isinstance(d, datetime.date)):
        return coarse_datetime_repr(d)
    return default

def get_creation_date(object, default):
    return _get_date_or_datetime(object, 'created', default)

def get_modified_date(object, default):
    return _get_date_or_datetime(object, 'modified', default)

def get_content_modified_date(object, default):
    return _get_date_or_datetime(object, 'content_modified', default)

def get_start_date(object, default):
    # For monthly browsing of calendar events
    return _get_date_or_datetime(object, 'startDate', default)

def get_end_date(object, default):
    # For monthly browsing of calendar events
    return _get_date_or_datetime(object, 'endDate', default)

def get_publication_date(object, default):
    return _get_date_or_datetime(object, 'publication_date', default)

def get_mimetype(object, default):
    mimetype = getattr(object, 'mimetype', None)
    if mimetype is None:
        return default
    return mimetype

def get_creator(object, default):
    creator = getattr(object, 'creator', None)
    if creator is None:
        return default
    return creator

def get_modified_by(object, default):
    userid = getattr(object, 'modified_by', None)
    if userid is None:
        return default
    return userid

def get_email(object, default):
    email = getattr(object, 'email', None)
    if email is None:
        return default
    return email.lower()

def get_allowed_to_view(object, default):
    principals = principals_allowed_by_permission(object, 'view')
    if not principals:
        # An empty value tells the catalog to match anything, whereas when
        # there are no principals with permission to view we want for there
        # to be no matches.
        principals = ['NO ONE no way NO HOW',]
    return principals

def get_lastfirst(object, default):
    if not IProfile.providedBy(object):
        return default
    return ('%s, %s' % (object.lastname, object.firstname)).lower()

def get_member_name(object, default):
    if not IProfile.providedBy(object):
        return default
    return ('%s %s' % (object.firstname, object.lastname)).lower()

def get_virtual(object, default):
    adapter = queryAdapter(object, IVirtualData)
    if adapter is not None:
        return adapter()
    return default

class Site(Folder):
    implements(ISite, ILocation)
    __name__ = None
    __parent__ = None
    __acl__ = [(Allow, Authenticated, 'view')]
    title = 'Site'
    list_aliases = None

    def __init__(self):
        super(Site, self).__init__()
        self.catalog = CachingCatalog()
        self.update_indexes()
        self.catalog.document_map = DocumentMap()

        profiles = create_content(IProfiles)
        self['profiles'] = profiles
        communities = create_content(ICommunities)
        self['communities'] = communities
        self.users = KARLUsers(self)
        self.tags = Tags(self)
        self.sessions = SessionDataManager(3600, 5)
        self.filestore = PersistentMapping()
        self.list_aliases = OOBTree()

    def update_indexes(self):
        """ Ensure that we have indexes matching what the application needs.

        This function is called when the site is first created, and again
        whenever the ``reindex_catalog`` script is run.

        Extensions can arrange to get their own indexes added by registering
        named utilities for the
        :interface:`karl.models.interfaces.IIndexFactory` interface:  each
        such interface will be called to create a new (or overwritten) index.
        """
        indexes = {
            'name': CatalogFieldIndex(get_name),
            'title': CatalogFieldIndex(get_title), # used as sort index
            'titlestartswith': CatalogFieldIndex(get_title_firstletter),
            'interfaces': CatalogKeywordIndex(get_interfaces),
            'texts': CatalogTextIndex(get_textrepr),
            'path': CatalogPathIndex2(get_path, attr_discriminator=get_acl),
            'allowed':CatalogKeywordIndex(get_allowed_to_view),
            'creation_date': CatalogFieldIndex(get_creation_date),
            'modified_date': CatalogFieldIndex(get_modified_date),
            'content_modified': CatalogFieldIndex(get_content_modified_date),
            'start_date': CatalogFieldIndex(get_start_date),
            'end_date': CatalogFieldIndex(get_end_date),
            'publication_date': CatalogFieldIndex(get_publication_date),
            'mimetype': CatalogFieldIndex(get_mimetype),
            'creator': CatalogFieldIndex(get_creator),
            'modified_by': CatalogFieldIndex(get_modified_by),
            'email': CatalogFieldIndex(get_email),
            'tags': TagIndex(self),
            'lastfirst': CatalogFieldIndex(get_lastfirst),
            'member_name': CatalogTextIndex(get_member_name),
            'virtual':CatalogFieldIndex(get_virtual),
            }

        for name, utility in getUtilitiesFor(IIndexFactory):
            indexes[name] = utility()

        catalog = self.catalog

        # add indexes
        for name, index in indexes.iteritems():
            if name not in catalog:
                catalog[name] = index

        # remove indexes
        for name in catalog.keys():
            if name not in indexes:
                del catalog[name]

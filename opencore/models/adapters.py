import warnings

from ZODB.POSException import POSKeyError

from repoze.bfg.interfaces import ILogger
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import effective_principals
from repoze.bfg.traversal import find_model
from repoze.bfg.traversal import model_path
from repoze.bfg.traversal import find_interface
from repoze.bfg.url import model_url
from repoze.lemonade.listitem import get_listitems
from zope.component import queryUtility
from zope.interface import implements

from opencore.consts import countries
from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IComment
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import ICommunityInfo
from opencore.models.interfaces import IGridEntryInfo
from opencore.models.interfaces import ITagQuery
from opencore.models.interfaces import IToolFactory
from opencore.models.interfaces import ITextIndexData
from opencore.models.interfaces import IProfileDict
from opencore.models.profile import social_category
from opencore.utils import find_catalog
from opencore.utils import find_profiles
from opencore.utils import find_tags
from opencore.utils import get_content_type_name
from opencore.utils import get_setting

from opencore.utilities.image import thumb_url
from opencore.utilities.converters.interfaces import IConverter
from opencore.utilities.converters.entities import convert_entities
from opencore.utilities.converters.stripogram import html2text

import logging
log = logging.getLogger(__name__)


class CatalogSearch(object):
    """ Centralize policies about searching """
    implements(ICatalogSearch)
    def __init__(self, context, request=None):
        # XXX request argument is not used, is left in for backwards
        #     compatability.  Should be phased out.
        self.context = context
        self.catalog = find_catalog(self.context)
        if request is not None:
            warnings.warn('Creating CatalogSearch with request is deprecated.',
                          DeprecationWarning, stacklevel=2)

    def __call__(self, **kw):
        num, docids = self.catalog.search(**kw)
        address = self.catalog.document_map.address_for_docid
        logger = queryUtility(ILogger, 'repoze.bfg.debug')
        def resolver(docid):
            path = address(docid)
            if path is None:
                return None
            try:
                return find_model(self.context, path)
            except KeyError:
                logger and logger.warn('Model missing: %s' % path)
                return None
        return num, docids, resolver



class GridEntryInfo(object):
    implements(IGridEntryInfo)
    _type = None
    _url = None
    _modified = None
    _created = None
    _creator_title = None
    _creator_url = None
    _profiles = None
    _profile = None  # profile of creator
    _modified_by_profile = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def title(self):
        return self.context.title

    @property
    def url(self):
        if self._url is None:
            if IComment.providedBy(self.context):
                # show the comment in context of its grandparent.
                # (its parent is a comments folder.)
                parent = self.context.__parent__.__parent__
                self._url = '%s#comment-%s' % (
                    model_url(parent, self.request), self.context.__name__)
            else:
                self._url = model_url(self.context, self.request)
        return self._url

    @property
    def type(self):
        if self._type is None:
            self._type = get_content_type_name(self.context)
        return self._type

    @property
    def modified(self):
        if self._modified is None:
            self._modified = self.context.modified.strftime("%m/%d/%Y")
        return self._modified

    @property
    def created(self):
        if self._created is None:
            self._created = self.context.created.strftime("%m/%d/%Y")
        return self._created

    @property
    def creator_title(self):
        if self._profiles is None:
            self._profiles = find_profiles(self.context)
        if self._profile is None:
            self._profile = self._profiles.get(self.context.creator, None)
        if self._creator_title is None:
            self._creator_title = getattr(self._profile, "title",
                                          "no profile title")
        return self._creator_title

    @property
    def creator_url(self):
        if self._profiles is None:
            self._profiles = find_profiles(self.context)
        if self._profile is None:
            self._profile = self._profiles.get(self.context.creator, None)
        if self._creator_url is None:
            self._creator_url = model_url(self._profile, self.request)
        return self._creator_url

    @property
    def modified_by_profile(self):
        if self._modified_by_profile is None:
            modified_by = getattr(self.context, 'modified_by', None)
            if modified_by is None:
                modified_by = self.context.creator
            if self._profiles is None:
                self._profiles = find_profiles(self.context)
            self._modified_by_profile = self._profiles.get(modified_by, None)
        return self._modified_by_profile

    @property
    def modified_by_title(self):
        return getattr(self.modified_by_profile, 'title', 'no profile title')

    @property
    def modified_by_url(self):
        return model_url(self.modified_by_profile, self.request)

    def __str__(self ):
        return 'GridEntryInfo: title=%s, url=%s, type=%s, modified=%s, ' \
         'created=%s, creator_title=%s, creator_url=%s, ' \
         'modified_by_profile=%s, modified_by_title=%s, modified_by_url=%s' % \
      (self.title, self.url, self.type, self.modified, self.created,
       self.creator_title, self.creator_url, self.modified_by_profile,
       self.modified_by_title, self.modified_by_url)


class TagQuery(object):
    implements(ITagQuery)
    _docid = None
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.username = authenticated_userid(request)
        self.path = model_path(context)
        self.catalog = find_catalog(context)
        self.tags = find_tags(context)

    @property
    def docid(self):
        if self._docid is None:
            self._docid = self.catalog.document_map.docid_for_address(
                                                                self.path)
        return self._docid

    @property
    def usertags(self):
        return self.tags.getTags(users=(self.username,), items=(self.docid,))

    @property
    def tagswithcounts(self):
        """Return tags on a resource, including people and counts"""

        # To draw the tagbox on a resource, we need to know all the
        # tags.  For each tag, the count of people that tagged the
        # resource and if the current user was a tagger.
        tagObjects = self.tags.getTagObjects(items=(self.docid,))
        tagObjects = sorted(tagObjects, key=lambda x: (x.name, x.user))
        alltaginfo = []
        count = 0
        current = None
        current_users = []
        for tagObj in tagObjects:
            if tagObj.name != current:
                if current is not None:
                    alltaginfo.append({
                            'tag': current,
                            'count': len(current_users),
                            'snippet': (self.username not in current_users
                                            and 'nondeleteable' or ''),
                            })
                current = tagObj.name
                count = 1
                current_users = [tagObj.user]
            else:
                count += 1
                current_users.append(tagObj.user)
        if current is not None:
            alltaginfo.append({
                    'tag': current,
                    'count': len(current_users),
                    'snippet': (self.username not in current_users
                                    and 'nondeleteable' or ''),
                    })

        # Sort the tags alphabetically
        return sorted(alltaginfo, key=lambda r: r['tag'])

    @property
    def tagusers(self):
        taginfo = " ".join(self.usertags)
        return taginfo

    def tags_with_prefix(self, prefix):
        return self.tags.getTagsWithPrefix(prefix)


class CommunityInfo(object):
    implements(ICommunityInfo)
    _url = None
    _tabs = None
    _content_modified = None
    _number_of_members = None
    _tags = None

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.name = self.context.__name__
        self.title = self.context.title
        self.description = self.context.description

    @property
    def tags(self):
        if self._tags is None:
            self._tags = find_tags(self.context)
        return self._tags

    @property
    def number_of_members(self):
        if self._number_of_members is None:
            self._number_of_members = self.context.number_of_members
        return self._number_of_members

    @property
    def url(self):
        if self._url is None:
            self._url = model_url(self.context, self.request)
        return self._url

    @property
    def last_activity_date(self):
        if self._content_modified is None:
            # we avoid use of strftime here to banish it from profiler
            # output (for /communities), although this is probably no
            # faster IRL
            m = self.context.content_modified
            self._content_modified = '%02d/%02d/%s' % (m.month, m.day, m.year)
        return self._content_modified

    @property
    def tabs(self):
        if self._tabs is None:

            found_current = False

            overview_css_class = ''

            if ( ICommunity.providedBy(self.request.context) and
                 self.request.view_name in ['','view.html'] ):
                overview_css_class = 'curr'
                found_current = True

            tabs = [
                {'url':model_url(self.context, self.request, 'view.html'),
                 'css_class':overview_css_class,
                 'name':'OVERVIEW'}
                ]

            for toolinfo in get_listitems(IToolFactory):
                toolfactory = toolinfo['component']
                if toolfactory.is_present(self.context, self.request):
                    info = {}
                    info['url'] = toolfactory.tab_url(self.context,
                                                      self.request)
                    info['css_class'] = ''
                    if not found_current:
                        if toolfactory.is_current(self.context, self.request):
                            info['css_class'] = 'curr'
                            found_current = True
                    info['name'] = toolinfo['title'].upper()
                    tabs.append(info)

            self._tabs = tabs

        return self._tabs

    @property
    def community_tags(self):
        """ Return data for tags portlet on community pages

        o Return the top five, sorted in reverse order by count.
        """
        if self.tags is None:
            return ()

        raw = self.tags.getFrequency(community=self.context.__name__)
        result = []
        for tag, count in sorted(raw, key=lambda x: x[1], reverse=True)[:5]:
            result.append({'tag': tag, 'count': count})
        return result

    @property
    def member(self):
        principals = set(effective_principals(self.request))
        members = set(self.context.member_names)
        return bool(principals & members)

    @property
    def moderator(self):
        username = authenticated_userid(self.request)
        return username in self.context.moderator_names


class FlexibleTextIndexData(object):

    implements(ITextIndexData)

    ATTR_WEIGHT_CLEANER = [('title', 10, None),
                           ('description', 1, None),
                           ('text', 1, None),
                          ]

    def __init__(self, context):
        self.context = context

    def __call__(self):
        parts = []
        for attr, weight, cleaner in self.ATTR_WEIGHT_CLEANER:
            if callable(attr):
                value = attr(self.context)
            else:
                value = getattr(self.context, attr, None)
            if value is not None:
                if cleaner is not None:
                    value = cleaner(value)
                parts.extend([value] * weight)
        return ' '.join(filter(None, parts))

def makeFlexibleTextIndexData(attr_weights):
    if not attr_weights:
        raise ValueError('Must have at least one (attr, weight).')
    class Derived(FlexibleTextIndexData):
        ATTR_WEIGHT_CLEANER = attr_weights
    return Derived

def extract_text_from_html(text):
    if not isinstance(text, unicode):
        text = unicode(text, 'utf-8', 'replace')
    return html2text(convert_entities(text))

TitleAndDescriptionIndexData = makeFlexibleTextIndexData(
                                [('title', 10, None),
                                 ('description', 1, None),
                                ])

TitleAndTextIndexData = makeFlexibleTextIndexData(
                                [('title', 10, None),
                                 ('text', 1, extract_text_from_html),
                                ])

def _extract_and_cache_file_data(context):
    data = getattr(context, '_extracted_data', None)
    if data is None:
        context._extracted_data = data = _extract_file_data(context)
    return data

def _extract_file_data(context):
    converter = queryUtility(IConverter, context.mimetype)
    if converter is None:
        return ''
    try:
        blobfile = context.blobfile
        if hasattr(blobfile, '_current_filename'):
            # ZODB < 3.9
            filename = context.blobfile._current_filename()
        else:
            # ZODB >= 3.9
            filename = blobfile._p_blob_uncommitted
            if not filename:
                filename = blobfile._p_blob_committed
            if not filename:
                # Blob file does not exist on filesystem
                return ''
    except POSKeyError, why:
        if why[0] != 'No blob file':
            raise
        return ''

    try:
        stream, encoding = converter.convert(filename, encoding=None,
                                             mimetype=context.mimetype)
    except Exception, e:
        # Just won't get indexed
        log.exception("Error converting file %s" % filename)
        return ''

    datum = stream.read(1<<21) # XXX dont read too much into RAM
    if encoding is not None:
        try:
            datum = datum.decode(encoding)
        except UnicodeDecodeError:
            # XXX Temporary workaround to get import working
            # The "encoding" is a lie.  Coerce to ascii.
            log.error("Converted text is not %s: %s" %
                        (encoding, filename))
            if len(datum) > 0:
                datum = repr(datum)[2:-2]

    return datum

FileTextIndexData = makeFlexibleTextIndexData(
                                [('title', 10, None),
                                 (_extract_and_cache_file_data, 1, None),
                                ])

class CalendarEventCategoryData(object):
    def __init__(self, context):
        self.context = context

    def __call__(self):
        category = getattr(self.context, 'calendar_category', None)
        if not category:
            calendar = find_interface(self.context, ICalendar)
            category = model_path(calendar)
        return category

class ProfileDict(dict):
    implements(IProfileDict)

    def update_details(self, context, request, api, photo_thumb_size):

        # Create display values from model object

        for name in [name for name in context.__dict__.keys() if not name.startswith("_")]:
            profile_value = getattr(context, name)
            if profile_value is not None:
                # Don't produce u'None'
                self[name] = unicode(profile_value)
            else:
                self[name] = None

        # 'websites' is a tuple, so unicode(websites) is not what we want
        self["websites"] = context.websites

        # 'title' is a property, so need to access it directly
        self["title"] = context.title

        # 'created' is also a property and needs formatting too
        self['created'] = context.created.strftime('%B %d, %Y')

        if self.has_key("languages"):
            self["languages"] = context.languages

        if self.has_key("department"):
            self["department"] = context.department

        if self.get("last_login_time"):
            stamp = context.last_login_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            self["last_login_time"] = stamp

        if self.has_key("country"):
            # translate from country code to country name
            country_code = self["country"]
            country = countries.as_dict.get(country_code, u'')
            self["country"] = country

        # Display portrait
        photo = context.get('photo')
        display_photo = {}
        if photo is not None:
            display_photo["url"] = thumb_url(photo, request, photo_thumb_size)
        else:
            display_photo["url"] = api.static_url + "/images/defaultUser.gif"
        self["photo"] = display_photo

        if get_setting(context, 'twitter_search_id'):
            # assume it's a social app
            social = social_category(context, None)
            if social:
                self.update(social.ids())

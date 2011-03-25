import time
import logging

from zope.interface import implements
from zope.component import getMultiAdapter
from zope.component import getAdapter

from webob import Response

from repoze.bfg.chameleon_zpt import render_template
from repoze.bfg.url import model_url
from repoze.bfg.traversal import model_path
from beaker.cache import cache_region
from opencore.utils import find_profiles
from opencore.views.community import get_recent_items_batch
from opencore.views.interfaces import IAtomFeed
from opencore.views.interfaces import IAtomEntry
from opencore.views.utils import convert_entities
from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import ICommunityContent
from opencore.models.interfaces import IImage
from opencore.utilities.image import thumb_url

N_ENTRIES = 20
log = logging.getLogger(__name__)

def format_datetime(d):
    formatted = d.strftime("%Y-%m-%dT%H:%M:%S")
    if d.tzinfo:
        tz = d.strftime("%z")
        assert len(tz) == 5
        formatted = "%s%s:%s" % (formatted, tz[:3], tz[3:])
    else:
        offset = -time.timezone
        sign = "-" if offset < 0 else "+"
        h, m = abs(offset / 3600), abs((offset % 3600) / 60)
        tz = "%s%02d:%02d" % (sign, h, m)
        formatted += tz

    return formatted

def xml_content(f):
    """
    A decorator for xml content which performs entity conversions from HTML
    to numeric XML-friendly entities.
    """
    def wrapper(*args, **kw):
        return convert_entities(f(*args, **kw))
    return wrapper

class AtomFeed(object):
    """ Atom/xml view.
    """
    implements(IAtomFeed)
    _entries = None
    _template = "templates/atomfeed.pt"
    _subtitle = u"Recent Items"

    def __init__(self, context, request):
        self.context = context
        self.request = request
        
        self._url = model_url(context, request)

    def __call__(self):
        xml = render_template(self._template, view=self)
        response = Response(xml, content_type="application/atom+xml")
        return response

    @property
    def title(self):
        return self.context.title

    @property
    def subtitle(self):
        return self._subtitle

    @property
    def link(self):
        return self._url

    id = link

    @property
    def entries(self):
        if self._entries is None:
            request = self.request
            def adapt(context):
                return getMultiAdapter((context, request), IAtomEntry)
            self._entries = map(adapt, self._entry_models)

        return self._entries

    @property
    def updated(self):
        models = self._entry_models
        if models:
            modified = models.pop(0).modified
            for model in models:
                modified = max(modified, model.modified)
            return format_datetime(modified)
        return format_datetime(self.context.modified)

    @property
    def _entry_models(self):
        """Provides actual content objects that need to be adapted to atom feed
        entries.
        """
        raise NotImplementedError(
            "Method must be overridden by concrete subclass.")

class AtomEntry(object):
    """ Abstract atom entry class that can adapt most model objects to an
    atom entry, except for the entry content.
    """
    implements(IAtomEntry)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def title(self):
        return self.context.title

    @property
    def uri(self):
        if IImage.providedBy(self.context):
            return thumb_url(self.context, self.request, (75,75))    
        return model_url(self.context, self.request)

    @property
    def published(self):
        return format_datetime(self.context.created)

    @property
    def updated(self):
        return format_datetime(self.context.modified)

    @property
    def author(self):
        profiles = find_profiles(self.context)
        profile = profiles[self.context.creator]
        return {
            "name": profile.title,
            "uri": model_url(profile, self.request)
        }

    @property
    def content(self):
        raise NotImplementedError(
            "Method must be overridden by concrete subclass.")

class NullContentAtomEntry(AtomEntry):
    """ An adapter for objects that don't really have textual content
    appropriate for including in a feed.
    """
    @property
    def content(self):
        return None

class GenericAtomEntry(AtomEntry):
    """ Can adapt any model object with a "text" or "description" attribute,
    favoring "text" if it is available.
    """
    @property
    @xml_content
    def content(self):
        if hasattr(self.context, "text"):
            return self.context.text
        if hasattr(self.context, "description"):
            return self.context.description
        return u""

class CommunityAtomFeed(AtomFeed):
    """ Presents "Recent Activity" for community as an atom feed.
    """
    _subtitle = u"Recent Activity"

    def __init__(self, context, request):
        assert ICommunity.providedBy(context)
        super(CommunityAtomFeed, self).__init__(context, request)

    @property
    def _entry_models(self):
        batch = get_recent_items_batch(self.context, self.request, size=20)
        return batch["entries"]

def community_atom_view(context, request):
    return CommunityAtomFeed(context, request)()

class ProfileAtomFeed(AtomFeed):
    @property
    def _entry_models(self):
        search = getAdapter(self.context, ICatalogSearch)
        count, docids, resolver = search(
            limit=N_ENTRIES,
            #path=model_path(self.context),
            creator=self.context.__name__,
            sort_index="modified_date",
            reverse=True,
            interfaces=[ICommunityContent,]
        )

        return [resolver(docid) for docid in docids]

def profile_atom_view(context, request):
    return ProfileAtomFeed(context, request)()

@cache_region('short_term', 'twitter_search')
def twitter_site_atom_view(context, request):
    from opencore.utils import fetch_url
    from opencore.utils import get_setting
    twitter_search_id = get_setting(context, 'twitter_search_id')
    if not twitter_search_id:
        raise ValueError('no value found for twitter_search_id in config (ini). Unable to search twitter.')
    search_url = 'http://search.twitter.com/search.rss?q=%s' % twitter_search_id
    log.debug('twitter_site_atom_view: GET %s' % search_url)
    feed_xml, headers = fetch_url(search_url)
    response = Response(feed_xml, content_type=headers['Content-Type'])
    # would be good to set the ETag too so the browser doesn't even try 
    # to hit the page unless its expired.
    log.debug('twitter_site_atom_view: %s' % response.headerlist)
    return response
    
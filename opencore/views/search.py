# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz@sorosny.org
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Site and community search views"""
import logging
from repoze.bfg.security import effective_principals
from repoze.bfg.traversal import model_path
from repoze.bfg.url import model_url
from repoze.lemonade.interfaces import IContent
from repoze.lemonade.listitem import get_listitems
from repoze.lemonade.content import get_content_types
from simplejson import JSONEncoder
from webob.exc import HTTPBadRequest
from webob import Response
from zope.component import queryUtility
from zope.index.text.parsetree import ParseError
import datetime

from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import IComment
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import IGroupSearchFactory
from opencore.models.interfaces import IProfile
from opencore.models.profile import Profile
from opencore.models.commenting import Comment
from opencore.utils import coarse_datetime_repr
from opencore.utils import get_content_type_name
from opencore.utils import get_setting
from opencore.views.api import TemplateAPI
from opencore.views.site import not_found
from opencore.views.batch import get_catalog_batch_grid

log = logging.getLogger(__name__)

def get_topic_options(context):
    topic_options = []
    topic_line = get_setting(context, "topics")

    if not topic_line:
        return topic_options

    for topic in topic_line.split('\n'):
        if topic != '':
            topic_options.append(topic)
    return topic_options

def advancedsearch_view(context, request):

    page_title = 'Advanced Search'
    api = request.api
    api.page_title = page_title

    type_choices = []
    for t in get_content_types():
        if t.queryTaggedValue('search_option', False):
            # this content type should be on the list of types to search
            iid = interface_id(t)
            name = t.queryTaggedValue('name', iid)
            type_choices.append((name, iid))
    type_choices.sort()

    this_year = datetime.datetime.now().year
    year_choices = [str(i) for i in range(2007, this_year+1)]
    topic_choices = get_topic_options(context)
    return dict(
        api=api,
        post_url=model_url(context, request, "searchresults.html"),
        topic_choices=topic_choices,
        type_choices=type_choices,
        year_choices=year_choices,
        )


def interface_id(t):
    return '%s_%s' % (t.__module__.replace('.', '_'), t.__name__)


def _iter_userids(context, request, profile_text):
    """Yield userids given a profile text search string."""
    search = ICatalogSearch(context)
    num, docids, resolver = search(
        interfaces=[IProfile], texts=profile_text)
    for docid in docids:
        profile = resolver(docid)
        if profile:
            yield profile.__name__


def make_query(context, request, search_interfaces=[]):
    """Given a search request, return a catalog query and a list of terms.
    """
    params = request.params
    query = {}
    terms = []
    body = params.get('body')
    if body:
        query['texts'] = body
        query['sort_index'] = 'texts'
        terms.append(body)

    creator = params.get('creator')
    if creator:
        userids = list(_iter_userids(context, request, creator))
        query['creator'] = {
            'query': userids,
            'operator': 'or',
            }
        terms.append(creator)

    types = params.getall('types')
    if types:
        type_dict = {}
        for t in get_content_types():
            type_dict[interface_id(t)] = t
        ifaces = [type_dict[name] for name in types]
        query['interfaces'] = {
            'query': ifaces,
            'operator': 'or',
            }
        terms.extend(iface.getTaggedValue('name') for iface in ifaces)
    else:
        query['interfaces'] = {
            'query': search_interfaces,
            'operator': 'or'
            }

    tags = params.getall('tags')
    if tags:
        query['tags'] = {
            'query': tags,
            'operator': 'or',
            }
        terms.extend(tags)

    topics = params.getall('topics')
    if topics:
        query['topics'] = {
            'query': topics,
            'operator': 'or',
            }
        terms.extend(topics)

    year = params.get('year')
    if year:
        year = int(year)
        begin = coarse_datetime_repr(datetime.datetime(year, 1, 1))
        end = coarse_datetime_repr(datetime.datetime(year, 12, 31, 12, 59, 59))
        query['creation_date'] = (begin, end)
        terms.append(year)

    return query, terms


def get_batch(context, request, search_interfaces=[IContent], filter_func=None):
    """Return a batch of results and term sequence for a search request.

    If the user provided no terms, the returned batch will be None and the
    term sequence will be empty.
    """
    batch = None
    terms = ()
    kind = request.params.get("kind")
    if not kind:
        # Search form
        query, terms = make_query(context, request, search_interfaces)
        log.debug('query: %s' % query)

        context_path = model_path(context)
        if context_path and context_path != '/':
            query['path'] = {'query': context_path}
        #principals = effective_principals(request)
        #query['allowed'] = {'query':principals, 'operator':'or'}
        batch = get_catalog_batch_grid(context, request, filter_func=filter_func, **query)

    else:
        # LiveSearch
        text_term = request.params.get('body')
        if text_term:
            searcher = queryUtility(IGroupSearchFactory, kind)
            if searcher is None:
                # If the 'kind' we got is not known, return an error
                fmt = "The LiveSearch group %s is not known"
                raise HTTPBadRequest(fmt % kind)

            batch = searcher(context, request, text_term).get_batch()
            terms = [text_term, kind]

    return batch, terms

class SearchResultsView(object):

    # The GET 'tab' parameter must be in the range below and subclasses
    # are free to extend it with values specific for their models.
    tabs_allowed = ['general', 'members']

    # Depending on the 'tab' parameter, different interfaces will be taken into
    # account by the search engine. Subclasses should keep it in sync with
    # the 'tabs_allowed' list above.
    tabs_to_interfaces = {
        'general': [IContent],
        'members': [IProfile],
    }

    # Mapping between the search result item's type and the name of the key
    # under which it will be put in the view's result dict. Can't really use
    # interfaces instead of classes because many type will share common
    # interfaces.
    type_to_result_dict = {
        Comment: 'comments',
        Profile: 'members'
    }

    # Subclasses may wish to override the attribute and make it a method for
    # filtering out the result right before it's broken into smaller batches.
    # Default implementation is a None attribute for performance reasons,
    # the search engine's logic will figure out it's None and won't try executing
    # a non-existing method, thus saving time on a pass-through call.
    pre_batch_filter = None

    # Subclasses may wish to define a method with that name. The method will
    # be called for each element in the results list, after the batching will
    # have been completed.
    post_batch_func = None
    
    # May be overridden in subclasses. Will be called right before the search
    # will return the results.
    pre_return_func = None
    

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):

        # Either terms or at least one topic must be provided to guard
        # against abuses.
        has_topic = self.request.params.get('topics')
        has_terms = self.request.params.get('body')
        has_country = self.request.params.get('country')

        if not(has_topic or has_terms or has_country):
            msg = "Expected at least one search term, a topic or a country, returning HTTP 404"
            log.error(msg)
            return not_found(self.context, self.request)

        # Get the name of the tab or assume it's a 'General' one in case
        # the parameter's missing.
        tab = self.request.params.get('tab')
        if not tab:
            tab = 'general'

        if not tab in self.tabs_allowed:
            msg = "GET 'tab' must be one of %s not [%s], returning HTTP 404" % (
                self.tabs_allowed, tab)
            log.error(msg)
            return not_found(self.context, self.request)

        page_title = 'Search results'

        api = self.request.api
        api.page_title = page_title
        if ICommunity.providedBy(self.context):
            layout = api.community_layout
            community = self.context.title
        else:
            layout = api.generic_layout
            community = None

        batch = None
        terms = ()
        error = None

        try:
            search_interfaces = self.tabs_to_interfaces[tab]
            batch, terms = get_batch(self.context, self.request, search_interfaces,
                                     self.pre_batch_filter)
        except ParseError, e:
            error = 'Error: %s' % e

        if batch:
            # Prepare the keys for result list. In the worst case, each key
            # will point to an empty list.
            results = []
            
            for result in batch['entries']:
                result.url = model_url(result, self.request)
                if self.post_batch_func:
                    result = self.post_batch_func(result)

                results.append(result)

            total = batch['total']
        else:
            batch = {'batching_required': False}
            results = {}
            total = 0

        return_data = dict(
            api=api,
            layout=layout,
            error=error,
            terms=terms,
            community=community,
            results=results,
            total=total,
            batch_info=batch,
            query=self.request.params.get('body'),
            )

        if self.pre_return_func:
            return_data = self.pre_return_func(return_data)
        
        return return_data


class LivesearchResults(list):

    def __init__(self):
        list.__init__(self)
        self.set_header('')

    def set_header(self, header, pre="", post=""):
        self.header = header
        self.pre = pre
        self.post = post

    def append_to(self, title, href, rowclass):
        if self.header:
            rowclass += ' hasheader'
        self.append(dict(
                rowclass = rowclass,
                header = self.header,
                title = title,
                href = href,
                pre = self.pre,
                post = self.post,
                ))
        self.set_header('')


def jquery_livesearch_view(context, request):
    # Prefix search is with a wildcard at the end
    try:
        searchterm = request.params.get('val', None)
    except UnicodeDecodeError:
        # Probably windows client didn't set request encoding. Try again.
        request.charset = 'ISO-8859-1'
        searchterm = request.params.get('val', None)

    if searchterm is None:
        # The request forgot to send the key we use to do a search, so
        # make a friendly error message.  Important for the unit test.
        msg = "Client failed to send a 'val' parameter as the searchterm"
        return HTTPBadRequest(msg)
    else:
        searchterm = searchterm + '*'

    records = LivesearchResults()

    records.set_header('',
        pre = '<div class="header"></div>',
        )
    records.append_to(
        rowclass = 'showall',
        title = 'Show All',
        href = model_url(context, request, 'searchresults.html',
                    query = {'body':searchterm},
                    ),
            )

    for listitem in get_listitems(IGroupSearchFactory):
        utility = listitem['component']

        factory = utility(context, request, searchterm)

        if factory is None:
            continue

        try:
            num, docids, resolver = factory()
        except ParseError:
            continue

        groupname = listitem['title']

        records.set_header(groupname,
            pre = '<div class="header">%s</div>' % (groupname, ),
            )

        results = filter(None, map(resolver, docids))

        qs = {'body':searchterm, 'kind':groupname}
        sr_href = model_url(context, request, 'searchresults.html', query=qs)

        for result in results:
            records.append_to(
                rowclass = 'result',
                title = getattr(result, 'title', '<No Title>'),
                href = model_url(result, request),
                )

        if results:
            records.append_to(
                rowclass = 'showall',
                title = 'Show All',
                href = sr_href,
                )
        else:
            records.append_to(
                rowclass = 'noresult',
                title = 'No Result',
                href = sr_href,
                )

    result = JSONEncoder().encode(list(records))
    return Response(result, content_type="application/x-json")

# Copyright (C) 2008-2009 Open Society Institute
#               !!! The original copyright holder !!!
#               2010-2011 Large Blue
#               Fergus Doyle: fergus.doyle@largeblue.com
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

"""Content feeds views
"""

# stdlib
import logging
from itertools import islice
from urlparse import urljoin

# Zope
from zope.component import getUtility

# Repoze
from repoze.bfg.security import effective_principals
from repoze.bfg.security import authenticated_userid

# opencore
from opencore.models.interfaces import IProfileDict
from opencore.utils import find_events
from opencore.views.people import get_profile_actions
from opencore.views.api import TemplateAPI

log = logging.getLogger(__name__)

_FILTER_COOKIE = 'opencore.feed_filter'


def _get_criteria(request):
    principals = effective_principals(request)
    principals = [x for x in principals if not x.startswith('system.')]

    # Check to see if we're asking for only "my" communities.
    filterby = request.params.get('filter', '')
    # cookie must be set even if param is empty or non-existent, to make
    # the no-filter button sticky.
    header = ('Set-Cookie', '%s=%s; Path=/' % (_FILTER_COOKIE, str(filterby)))
    request.cookies[_FILTER_COOKIE] = filterby
    request.response_headerlist = [header]

    if filterby == 'mycommunities':
        principals = [x for x in principals if not x.startswith('group.Karl')]

    if filterby == 'mycontent':
        created_by = authenticated_userid(request)
    elif filterby.startswith('profile:'):
        created_by = filterby[len('profile:'):]
    elif filterby.startswith('community:'):
        created_by = None
        community = filterby[len('community:'):]
        prefix = 'group.community:%s' % community
        principals = [x for x in principals if x.startswith(prefix)]
    else:
        created_by = None
        principals = None

    return principals, created_by

def _update_feed_items(entries, app_url):
    if not app_url.endswith('/'):
        app_url += '/'

    def reroot(fi, name):
        if name not in fi:
            return
        url = fi[name]
        if url is None:
            return
        if url.startswith('/'):
            url = url[1:]
        fi[name] = urljoin(app_url, url)

    feed_items = [dict(x[2]) for x in entries]

    for fi in feed_items:
        fi['timeago'] = str(fi.pop('timestamp').strftime('%Y-%m-%dT%H:%M:%SZ'))
        reroot(fi, 'url')
        reroot(fi, 'context_url')
        reroot(fi, 'profile_url')
        reroot(fi, 'thumbnail')
        del fi['allowed']

    return feed_items

def newest_feed_items(context, request):

    principals, created_by = _get_criteria(request)
    events = find_events(context)

    # Check to see if we're asking for most recent
    newer_than = request.params.get('newer_than')

    if newer_than:
        last_gen, last_index = newer_than.split(':')
        last_gen = long(last_gen)
        last_index = int(last_index)
        latest = list(events.newer(last_gen, last_index,
                                   principals, created_by))
    else:
        last_gen = -1L
        last_index = -1
        latest = list(islice(events.checked(principals, created_by), 20))

    if not latest:
        return (last_gen, last_index, last_gen, last_index, ())

    last_gen, last_index, ignored = latest[0]
    earliest_gen, earliest_index, ignored = latest[-1]

    feed_items = _update_feed_items(latest, request.application_url)

    return last_gen, last_index, earliest_gen, earliest_index, feed_items


def older_feed_items(context, request):
    older_than = request.params.get('older_than')

    # If we don't have params, bail out.
    if older_than is None:
        return -1, -1, ()

    principals, created_by = _get_criteria(request)
    events = find_events(context)

    earliest_gen, earliest_index = older_than.split(':')
    earliest_gen = long(earliest_gen)
    earliest_index = int(earliest_index)
    older = list(islice(events.older(earliest_gen, earliest_index,
                                principals, created_by), 20))

    if not older:
        return (earliest_gen, earliest_index, ())

    earliest_gen, earliest_index, ignored = older[-1]

    feed_items = _update_feed_items(older, request.application_url)

    return earliest_gen, earliest_index, feed_items


def show_feeds_view(context, request):
    api = request.api
    api.page_title = 'Latest Activity'
    filter_cookie = request.cookies.get(_FILTER_COOKIE) or ''
    return {'api': api,
            'show_filter': True,
            'sticky_filter': filter_cookie,
           }


def profile_feed_view(context, request):
    api = request.api
    api.page_title = 'Activity Feed'

    photo_thumb_size = (220,150)
    profile = getUtility(IProfileDict, name='profile-details')
    profile.update_details(context, request, api, photo_thumb_size)
    profile.photo_thumb_size = photo_thumb_size
    actions = get_profile_actions(context, request)

    return {'api': api,
            'show_filter': False,
            'sticky_filter': 'profile:%s' % context.__name__,
            'actions': actions,
            'profile_currently_viewed':profile,
           }


def community_feed_view(context, request):
    api = request.api
    api.page_title = 'Latest Activity'
    return {'api': api,
            'show_filter': False,
            'sticky_filter': 'community:%s' % context.__name__,
           }

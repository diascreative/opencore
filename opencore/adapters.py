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

from email.message import Message
import string
import warnings

from repoze.bfg.interfaces import ILogger
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import effective_principals
from repoze.bfg.traversal import find_interface
from repoze.bfg.traversal import find_model
from repoze.bfg.traversal import model_path
from repoze.bfg.url import model_url
from repoze.lemonade.listitem import get_listitems
from repoze.sendmail.interfaces import IMailDelivery
from zope.component import getUtility
from zope.component import queryUtility
from zope.interface import implements
from zope.component.event import objectEventNotify

from opencore.interfaces import ICatalogSearch
from opencore.interfaces import IComment
from opencore.interfaces import ICommunities
from opencore.interfaces import ICommunity
from opencore.interfaces import ICommunityInfo
from opencore.interfaces import IGridEntryInfo
from opencore.interfaces import IProfiles
from opencore.interfaces import ITagQuery
from opencore.interfaces import IToolFactory
from opencore.utils import find_catalog
from opencore.utils import find_profiles
from opencore.utils import find_tags
from opencore.utils import get_content_type_name
from opencore.utils import get_setting

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

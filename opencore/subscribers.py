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

from datetime import datetime
import math
import os
from pprint import pformat

from zope.component import queryUtility

from repoze.bfg.interfaces import ISettings
from repoze.bfg.traversal import model_path
from repoze.bfg.traversal import find_interface
from repoze.folder.interfaces import IFolder
from repoze.lemonade.content import is_content

from opencore.interfaces import ICommunity
from opencore.interfaces import IProfile
from opencore.utils import find_catalog
from opencore.utils import find_profiles
from opencore.utils import find_site
from opencore.utils import find_tags
from opencore.utils import find_users

_NOW = None
def _now():     # unittests can replace this to get known results
    return _NOW or datetime.now()

def postorder(startnode):
    def visit(node):
        if IFolder.providedBy(node):
            for child in node.values():
                for result in visit(child):
                    yield result
        yield node
    return visit(startnode)

def index_content(obj, event):
    """ Index content (an IObjectAddedEvent subscriber) """
    catalog = find_catalog(obj)
    if catalog is not None:
        for node in postorder(obj):
            if is_content(obj):
                path = model_path(node)
                docid = getattr(node, 'docid', None)
                if docid is None:
                    docid = node.docid = catalog.document_map.add(path)
                else:
                    catalog.document_map.add(path, docid)
                catalog.index_doc(docid, node)

def unindex_content(obj, docids):
    """ Unindex given 'docids'.
    """
    catalog = find_catalog(obj)
    if catalog is not None:
        for docid in docids:
            catalog.unindex_doc(docid)
            catalog.document_map.remove_docid(docid)

def cleanup_content_tags(obj, docids):
    """ Remove any tags associated with 'docids'.
    """
    tags = find_tags(obj)
    if tags is not None:
        for docid in docids:
            tags.delete(item=docid)

def handle_content_removed(obj, event):
    """ IObjectWillBeRemovedEvent subscriber.
    """
    catalog = find_catalog(obj)
    if catalog is not None:
        path = model_path(obj)
        num, docids = catalog.search(path={'query': path,
                                           'include_path': True})
        unindex_content(obj, docids)
        cleanup_content_tags(obj, docids)

def reindex_content(obj, event):
    """ Reindex a single piece of content (non-recursive); an
    IObjectModifed event subscriber """
    catalog = find_catalog(obj)
    if catalog is not None:
        path = model_path(obj)
        docid = catalog.document_map.docid_for_address(path)
        catalog.reindex_doc(docid, obj)

def set_modified(obj, event):
    """ Set the modified date on a single piece of content.
    
    This subscriber is non-recursive.
    
    Intended use is as an IObjectModified event subscriber.
    """
    if is_content(obj):
        now = _now()
        obj.modified = now
        _modify_community(obj, now)

def set_created(obj, event):
    """ Add modified and created attributes to obj and children.
    
    Only add to content objects which do not yet have them (recursively)
    
    Intended use is as an IObjectWillBeAddedEvent subscriber.
    """
    now = _now()
    for node in postorder(obj):
        if is_content(obj):
            if not getattr(node, 'modified', None):
                node.modified = now
            if not getattr(node, 'created', None):
                node.created = now
    parent = getattr(event, 'parent', None)
    if parent is not None:
        _modify_community(parent, now)

def _modify_community(obj, when):
    # manage content_modified on community whenever a piece of content
    # in a community is changed
    community = find_interface(obj, ICommunity)
    if community is not None:
        community.content_modified = when
        catalog = find_catalog(community)
        if catalog is not None:  # may not be wired into the site yet
            index = catalog.get('content_modified')
            if index is not None:
                index.index_doc(community.docid, community)

def delete_community(obj, event):
    # delete the groups related to the community when a community is
    # deleted
    context = obj
    users = find_users(context)
    users.delete_group(context.members_group_name)
    users.delete_group(context.moderators_group_name)

# Add / remove list aliases from the root 'list_aliases' index.

def add_mailinglist(obj, event):
    aliases = find_site(obj).list_aliases
    aliases[obj.short_address] = model_path(obj.__parent__)

def remove_mailinglist(obj, event):
    aliases = find_site(obj).list_aliases
    try:
        del aliases[obj.short_address]
    except KeyError:
        pass

# "Index" profile e-mails into the profiles folder.

def _remove_email(parent, name):
    mapping = getattr(parent, 'email_to_name')
    filtered = [x for x in mapping.items() if x[1] != name]
    mapping.clear()
    mapping.update(filtered)

def profile_added(obj, event):
    parent = obj.__parent__
    name = obj.__name__
    _remove_email(parent, name)
    parent.email_to_name[obj.email] = name

def profile_removed(obj, event):
    parent = obj.__parent__
    name = obj.__name__
    _remove_email(parent, name)


class QueryLogger(object):
    """Event listener that logs ICatalogQueryEvents to a directory.

    Performs 2 tasks:
    1. Divides the log files by the magnitude of the query duration,
       making it easy to find expensive queries.
    2. Log all queries to a single file for comparison across systems
    """

    def __init__(self):
        self._configured = False
        self.log_dir = None
        self.min_duration = None
        self.log_all = None

    def configure(self, settings):
        self.log_dir = getattr(settings, 'query_log_dir', None)
        if self.log_dir:
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
        self.min_duration = float(
            getattr(settings, 'query_log_min_duration', 0.0))
        self.log_all = bool(
            getattr(settings, 'query_log_all', False))
        self._configured = True

    def __call__(self, event):
        if not self._configured:
            settings = queryUtility(ISettings)
            if settings is not None:
                self.configure(settings)
        if not self.log_dir:
            return
        t = datetime.now().isoformat()
        duration = event.duration
        query = '  ' + pformat(event.query).replace('\n', '\n  ')
        if self.log_all:
            self._log(t, duration, event.result[0], query)
        if duration >= self.min_duration:
            self._log_by_magnitude(t, duration, event.result[0], query)

    def _log(self, ts, duration, num_results, query, fname='everything.log'):
        msg = '%s %8.3f %6d\n%s\n' % (
            ts, duration, num_results, query)
        path = os.path.join(self.log_dir, fname)
        f = open(path, 'a')
        try:
            f.write(msg)
        finally:
            f.close()

    def _log_by_magnitude(self, ts, duration, num_results, query):
        magnitude = math.ceil(math.log(duration, 2))
        fn = '%07d.log' % int(1000 * 2**magnitude)
        self._log(ts, duration, num_results, query, fname=fn)

log_query = QueryLogger()

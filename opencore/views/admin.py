from __future__ import with_statement

from datetime import datetime
import logging
import codecs
from cStringIO import StringIO
import csv
from _csv import Error
import os
import re
import transaction
from paste.fileapp import FileApp
from webob import Response
from webob.exc import HTTPFound

from zope.component import getUtility

from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.exceptions import NotFound
from repoze.bfg.security import authenticated_userid
from repoze.bfg.traversal import find_model
from repoze.bfg.traversal import model_path
from repoze.bfg.url import model_url
from repoze.lemonade.content import create_content
from repoze.sendmail.interfaces import IMailDelivery
from repoze.workflow import get_workflow

from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import ICommunityContent
from opencore.models.interfaces import IProfile
from opencore.utilities.rename_user import rename_user

from opencore.utils import find_community
from opencore.utils import find_profiles
from opencore.utils import find_site
from opencore.utils import find_users
from opencore.utils import get_setting
from opencore.views.api import TemplateAPI
from opencore.views.utils import make_unique_name
from opencore.views.batch import get_fileline_batch

log = logging.getLogger(__name__)

class AdminTemplateAPI(TemplateAPI):

    def __init__(self, context, request, page_title=None):
        super(AdminTemplateAPI, self).__init__(context, request, page_title)
        syslog_view = get_setting(context, 'syslog_view', None)
        self.syslog_view_enabled = syslog_view != None
        self.has_logs = not not get_setting(context, 'logs_view', None)
        self.error_monitoring = not not get_setting(
            context, 'error_monitor_subsystems', None
        )
        statistics_folder = get_setting(context, 'statistics_folder', None)
        if statistics_folder is not None:
            csv_files = [fn for fn in os.listdir(statistics_folder)
                         if fn.endswith('.csv')]
            self.statistics_view_enabled = not not csv_files
        else:
            self.statistics_view_enabled = False

def _menu_macro():
    return get_template('templates/admin/menu.pt').macros['menu']

def admin_view(context, request):
    log.debug('admin menu=%s' % _menu_macro())
    return dict(
        api=AdminTemplateAPI(context, request, 'Admin UI'),
        menu=_menu_macro()
    )

def _content_selection_widget():
    return get_template('templates/admin/content_select.pt').macros['widget']

def _content_selection_grid():
    return get_template('templates/admin/content_select.pt').macros['grid']

def _format_date(d):
    return d.strftime("%m/%d/%Y %H:%M")

def _populate_content_selection_widget(context, request):
    """
    Returns a dict of parameters to be passed to the template that includes
    the content selection widget.
    """
    # Get communities list
    search = ICatalogSearch(context)
    count, docids, resolver = search(
        interfaces=[ICommunity],
        sort_index='title'
    )
    communities = []
    for docid in docids:
        community = resolver(docid)
        communities.append(dict(
            path=model_path(community),
            title=community.title,
        ))

    return dict(
        communities=communities,
        title_contains=request.params.get('title_contains', None),
        selected_community=request.params.get('community', None),
    )

def _grid_item(item, request):
    creator_name, creator_url = 'Unknown', None
    profiles = find_profiles(item)
    creator = getattr(item, 'creator', None)
    if creator is not None and creator in profiles:
        profile = profiles[creator]
        creator_name = profile.title
        creator_url = model_url(profile, request)

    return dict(
        path=model_path(item),
        url=model_url(item, request),
        title=item.title,
        modified=_format_date(item.modified),
        creator_name=creator_name,
        creator_url=creator_url,
    )

def _get_filtered_content(context, request, interfaces=None):
    if interfaces is None:
        interfaces = [ICommunityContent,]
    search = ICatalogSearch(context)
    search_terms = dict(
        interfaces={'query': interfaces, 'operator': 'or'},
    )

    community = request.params.get('community', '_any')
    if community != '_any':
        search_terms['path'] = community

    title_contains = request.params.get('title_contains', '')
    if title_contains:
        title_contains = title_contains.lower()
        search_terms['texts'] = title_contains

    if community == '_any' and not title_contains:
        # Avoid retrieving entire site
        return []

    items = []
    count, docids, resolver = search(**search_terms)
    for docid in docids:
        item = resolver(docid)
        if (title_contains and title_contains not in
            getattr(item, 'title', '').lower()):
            continue
        items.append(_grid_item(item, request))

        # Try not to run out of memory
        if hasattr(item, '_p_deactivate'):
            item._p_deactivate()

    items.sort(key=lambda x: x['path'])
    return items

def delete_content_view(context, request):
    api = AdminTemplateAPI(context, request, 'Admin UI: Delete Content')
    filtered_content = []

    if 'filter_content' in request.params:
        filtered_content = _get_filtered_content(context, request)
        if not filtered_content:
            api.status_message = 'No content matches your query.'

    if 'delete_content' in request.params:
        paths = request.params.getall('selected_content')
        if paths:
            for path in paths:
                try:
                    content = find_model(context, path)
                    del content.__parent__[content.__name__]
                except KeyError:
                    # Thrown by find_model if we've already deleted an
                    # ancestor of this node.  Can safely ignore becuase child
                    # node has been deleted along with ancestor.
                    pass

            if len(paths) == 1:
                status_message = 'Deleted one content item.'
            else:
                status_message = 'Deleted %d content items.' % len(paths)

            redirect_to = model_url(
                context, request, request.view_name,
                query=dict(status_message=status_message)
            )
            return HTTPFound(location=redirect_to)

    parms = dict(
        api=api,
        menu=_menu_macro(),
        content_select_widget=_content_selection_widget(),
        content_select_grid=_content_selection_grid(),
        filtered_content=filtered_content,
    )
    parms.update(_populate_content_selection_widget(context, request))
    return parms

class _DstNotFound(Exception):
    pass

def _find_dst_container(src_obj, dst_community):
    """
    Given a source object and a destination community, figures out the
    container insider the destination community where source object can be
    moved to.  For example, if source object is a blog entry in community
    `foo` (/communities/foo/blog/entry1) and we want to move it to the `bar`
    community, this will take the relative path of the source object from its
    community and attempt to find analogous containers inside of the
    destination community.  In this example, the relative container path is
    'blog', so we the destination container is /communities/bar/blog.'
    """
    src_container_path = model_path(src_obj.__parent__)
    src_community_path = model_path(find_community(src_obj))
    rel_container_path = src_container_path[len(src_community_path):]
    dst_container = dst_community
    for node_name in filter(None, rel_container_path.split('/')):
        dst_container = dst_container.get(node_name, None)
        if dst_container is None:
            raise _DstNotFound(
                'Path does not exist in destination community: %s' %
                model_path(dst_community) + rel_container_path
            )
    return dst_container

def move_content_view(context, request):
    """
    Move content from one community to another.  Only blog entries supported
    for now.  May or may not eventually expand to other content types.
    """
    api = AdminTemplateAPI(context, request, 'Admin UI: Move Content')
    filtered_content = []

    if 'filter_content' in request.params:
        # We're limiting ourselves to content that always lives in the same
        # place in each community, ie /blog, /calendar, /wiki, etc, so that
        # we can be pretty sure we can figure out where inside the destination
        # community we should move it to.
        filtered_content = _get_filtered_content(
            context, request, [IBlogEntry, IWikiPage, ICalendarEvent])
        if not filtered_content:
            api.error_message = 'No content matches your query.'

    if 'move_content' in request.params:
        to_community = request.params.get('to_community', '')
        if not to_community:
            api.error_message = 'Please specify destination community.'
        else:
            try:
                paths = request.params.getall('selected_content')
                dst_community = find_model(context, to_community)
                for path in paths:
                    obj = find_model(context, path)
                    dst_container = _find_dst_container(obj, dst_community)
                    name = make_unique_name(dst_container, obj.__name__)
                    del obj.__parent__[obj.__name__]
                    dst_container[name] = obj

                if len(paths) == 1:
                    status_message = 'Moved one content item.'
                else:
                    status_message = 'Moved %d content items.' % len(paths)

                redirect_to = model_url(
                    context, request, request.view_name,
                    query=dict(status_message=status_message)
                )
                return HTTPFound(location=redirect_to)
            except _DstNotFound, error:
                api.error_message = str(error)

    parms = dict(
        api=api,
        menu=_menu_macro(),
        content_select_widget=_content_selection_widget(),
        content_select_grid=_content_selection_grid(),
        filtered_content=filtered_content,
    )
    parms.update(_populate_content_selection_widget(context, request))
    return parms

def logs_view(context, request):
    log_paths = get_setting(context, 'logs_view')
    log_paths = map(os.path.abspath, log_paths.split())
    if len(log_paths) == 1:
        # Only one log file, just view that
        log = log_paths[0]

    else:
        # Make user pick a log file
        log = request.params.get('log', None)

        # Don't let users view arbitrary files on the filesystem
        if log not in log_paths:
            log = None

    if log is not None and os.path.exists(log):
        lines = codecs.open(log, encoding='utf-8',
                            errors='replace').readlines()
    else:
        lines = []

    return dict(
        api=AdminTemplateAPI(context, request),
        menu=_menu_macro(),
        logs=log_paths,
        log=log,
        lines=lines,
    )

def statistics_view(context, request):
    statistics_folder = get_setting(context, 'statistics_folder')
    csv_files = [fn for fn in os.listdir(statistics_folder)
                 if fn.endswith('.csv')]
    return dict(
        api=AdminTemplateAPI(context, request),
        menu=_menu_macro(),
        csv_files=csv_files
    )

def statistics_csv_view(request):
    statistics_folder = get_setting(request.context, 'statistics_folder')
    csv_file = request.matchdict.get('csv_file')
    if not csv_file.endswith('.csv'):
        raise NotFound()

    path = os.path.join(statistics_folder, csv_file)
    if not os.path.exists(path):
        raise NotFound()

    return request.get_response(FileApp(path).get)

def _decode(s):
    """
    Convert to unicode, by hook or crook.
    """
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError:
        # Will probably result in some junk characters but it's better than
        # nothing.
        return s.decode('latin-1')

def rename_or_merge_user_view(request, rename_user=rename_user):
    """
    Rename or merge users.
    """
    context = request.context
    api=AdminTemplateAPI(context, request)
    old_username = request.params.get('old_username')
    new_username = request.params.get('new_username')
    if old_username and new_username:
        merge = bool(request.params.get('merge'))
        rename_messages = StringIO()
        try:
            rename_user(context, old_username, new_username, merge=merge,
                        out=rename_messages)
            api.status_message = rename_messages.getvalue()
        except ValueError, e:
            api.error_message = str(e)

    return dict(
        api=api,
        menu=_menu_macro()
    )

def site_announcement_view(context, request):
    """
    Edit the text of the site announcement, which will be displayed on
    every page for every user of the site.
    """
    api = AdminTemplateAPI(context, request, 'Admin UI: Move Content')
    profile = api.find_profile(authenticated_userid(request))
    site = find_site(context)
    if 'submit-site-announcement' in request.params:
        annc = request.params.get('site-announcement-input', '').strip()
        log.debug('site-announcement-input: %s' % annc)
        if annc:
            # we only take the content of the first <p> tag, with
            # the <p> tags stripped
            paramatcher = re.compile('<[pP]\\b[^>]*>(.*?)</[pP]>')
            match = paramatcher.search(annc)
            if match is not None:
                annc = match.groups()[0]
            site.site_announcement = {
                    'text': annc,
                    'profile': profile,
                    'timestamp': datetime.now(),
                    }
    if 'remove-site-announcement' in request.params:
        site.site_announcement = {}
    # Update because it's initialized when the api is instantiated
    api.site_announcement = site.site_announcement
    return dict(
        api=api,
        menu=_menu_macro()
        )

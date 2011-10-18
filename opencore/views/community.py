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

from repoze.lemonade.content import create_content
from email.message import Message

from zope.component.event import objectEventNotify
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.component import getUtility
from zope.interface import implements
from webob.exc import HTTPFound

from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.chameleon_zpt import render_template
from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import effective_principals
from repoze.bfg.security import has_permission
from repoze.bfg.traversal import model_path
from repoze.bfg.url import model_url

from repoze.sendmail.interfaces import IMailDelivery

from opencore.events import ObjectWillBeModifiedEvent
from opencore.events import ObjectModifiedEvent

from opencore.models.interfaces import ICatalogSearch
from opencore.models.interfaces import ICommunity
from opencore.models.interfaces import ICommunityContent
from opencore.models.interfaces import IGridEntryInfo
from opencore.models.interfaces import IProfile
from opencore.models.interfaces import ITagQuery

from opencore.utils import get_layout_provider
from opencore.utils import find_profiles
from opencore.utils import find_users

from opencore.views.adapters import DefaultToolAddables
from opencore.views.api import TemplateAPI
from opencore.views.interfaces import ISidebar
from opencore.views.interfaces import IToolAddables
from opencore.views.utils import convert_to_script
from opencore.views.utils import make_name
from opencore.views.batch import get_catalog_batch_grid
from opencore.views.tags import get_tags_client_data
from opencore.views.tags import set_tags

from opencore.security.policy import DELETE_COMMUNITY
from opencore.security.policy import MODERATE


def get_recent_items_batch(community, request, size=10):
    batch = get_catalog_batch_grid(
        community, request, interfaces=[ICommunityContent],
        sort_index="modified_date", reverse=True, batch_size=size,
        path={'query': model_path(community)},
        allowed={'query': effective_principals(request), 'operator': 'or'},
    )
    return batch

def redirect_community_view(context, request):
    assert ICommunity.providedBy(context), str(type(context))

    default_tool = getattr(context, 'default_tool', None)
    if not default_tool:
        default_tool = 'view.html'
    return HTTPFound(location=model_url(context, request, default_tool))

def show_community_view(context, request):
    assert ICommunity.providedBy(context), str(type(context))

    user = authenticated_userid(request)
    page_title = 'View Community ' + context.title
    api = request.api
    api.page_title = page_title

    # provide client data for rendering current tags in the tagbox
    tagquery = getMultiAdapter((context, request), ITagQuery)
    client_json_data = {'tagbox': {'docid': tagquery.docid,
                                   'records': tagquery.tagswithcounts,
                                  },
                       }

    # Filter the actions based on permission
    actions = []
    if has_permission(MODERATE, context, request):
        actions.append(('Edit', 'edit.html'))

    # If user has permission to see this view then has permission to join.
    if not(user in context.member_names or user in context.moderator_names):
        actions.append(('Join', 'join.html'))

    if has_permission(DELETE_COMMUNITY, context, request):
        actions.append(('Delete', 'delete.html'))

    recent_items = []
    recent_items_batch = get_recent_items_batch(context, request)
    for item in recent_items_batch["entries"]:
        adapted = getMultiAdapter((item, request), IGridEntryInfo)
        recent_items.append(adapted)

    feed_url = model_url(context, request, "atom.xml")

    return {'api': api,
            'actions': actions,
            'recent_items': recent_items,
            'batch_info': recent_items_batch,
            'head_data': convert_to_script(client_json_data),
            'feed_url': feed_url,
           }

def community_recent_items_ajax_view(context, request):
    assert ICommunity.providedBy(context), str(type(context))

    recent_items = []
    recent_items_batch = get_recent_items_batch(context, request, 5)
    for item in recent_items_batch["entries"]:
        adapted = getMultiAdapter((item, request), IGridEntryInfo)
        recent_items.append(adapted)

    return {'items': recent_items}

def get_members_batch(community, request, size=10):
    mods = list(community.moderator_names)
    members = list(community.member_names - community.moderator_names)
    any = list(community.member_names | community.moderator_names)
    principals = effective_principals(request)
    searcher = ICatalogSearch(community)
    total, docids, resolver = searcher(interfaces=[IProfile],
                                       limit=size,
                                       name={'query': any,
                                             'operator': 'or'},
                                       allowed={'query': principals,
                                                'operator': 'or'},
                                      )
    mod_entries = []
    other_entries = []

    for docid in docids:
        model = resolver(docid)
        if model is not None:
            if model.__name__ in mods:
                mod_entries.append(model)
            else:
                other_entries.append(model)

    return (mod_entries + other_entries)[:size]


def community_members_ajax_view(context, request):
    assert ICommunity.providedBy(context), str(type(context))

    members = []
    members_batch = get_members_batch(context, request, 5)
    for item in members_batch:
        adapted = getMultiAdapter((item, request), IGridEntryInfo)
        adapted.moderator = item.__name__ in context.moderator_names
        members.append(adapted)

    return {'items': members}


def related_communities_ajax_view(context, request):
    assert ICommunity.providedBy(context), str(type(context))

    related = []
    principals = effective_principals(request)
    searcher = ICatalogSearch(context)
    search = ' OR '.join(context.title.lower().split())
    total, docids, resolver = searcher(interfaces=[ICommunity],
                                       limit=5,
                                       reverse=True,
                                       sort_index="modified_date",
                                       texts=search,
                                       allowed={'query': principals,
                                                'operator': 'or'},
                                      )
    for docid in docids:
        model = resolver(docid)
        if model is not None:
            if model is not context:
                adapted = getMultiAdapter((model, request), IGridEntryInfo)
                related.append(adapted)

    return {'items': related}


def get_available_tools(context, request):
    available_tools = []
    available_tools = queryMultiAdapter(
        (context, request), IToolAddables,
        default=DefaultToolAddables(context, request))()
    return available_tools

def join_community_view(context, request):
    """ User sends an email to community moderator(s) asking to join
    the community.  Email contains a link to "add_existing" view, in members,
    that a moderator can use to add member to the community.

    """
    assert ICommunity.providedBy(context)

    # Get logged in user
    profiles = find_profiles(context)
    user = authenticated_userid(request)
    profile = profiles[user]

    # Handle form submission
    if "form.submitted" in request.POST:
        message = request.POST.get("message", "")
        moderators = [profiles[id] for id in context.moderator_names]
        mail = Message()
        mail["From"] = "%s <%s>" % (profile.title, profile.email)
        mail["To"] = ",".join(
            ["%s <%s>" % (p.title, p.email) for p in moderators]
        )
        mail["Subject"] = "Request to join %s community" % context.title

        body_template = get_template("templates/email_join_community.pt")
        profile_url = model_url(profile, request)
        accept_url=model_url(context, request, "members", "add_existing.html",
                             query={"user_id": user})
        body = body_template(
            message=message,
            community_title=context.title,
            person_name=profile.title,
            profile_url=profile_url,
            accept_url=accept_url
        )

        if isinstance(body, unicode):
            body = body.encode("UTF-8")

        mail.set_payload(body, "UTF-8")
        mail.set_type("text/html")

        recipients = [p.email for p in moderators]
        mailer = getUtility(IMailDelivery)
        mailer.send(profile.email, recipients, mail)

        status_message = "Your request has been sent to the moderators."
        location = model_url(context, request,
                             query={"status_message": status_message})

        return HTTPFound(location=location)

    # Show form
    page_title = "Join " + context.title
    api = request.api
    api.page_title = page_title
    return render_template_to_response(
        "templates/join_community.pt",
        api=api,
        profile=profile,
        community=context,
        post_url=model_url(context, request, "join.html"),
        formfields=api.formfields,
    )

def delete_community_view(context, request):

    page_title = 'Delete ' + context.title
    api = request.api
    api.page_title = page_title

    confirm = request.params.get('confirm', False)
    if confirm == '1':
        name = context.__name__
        del context.__parent__[name]
        location = model_url(context.__parent__, request)
        return HTTPFound(location=location)

    # Get a layout
    layout_provider = get_layout_provider(context, request)
    layout = layout_provider('community')

    return render_template_to_response(
        'templates/delete_resource.pt',
        api=api,
        layout=layout,
        num_children=0,
        )

class CommunitySidebar(object):
    implements(ISidebar)

    def __init__(self, context, request):
        pass

    def __call__(self, api):
        return render_template(
            'templates/community_sidebar.pt',
            api=api)

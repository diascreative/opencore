import datetime
import logging
from webob.exc import HTTPFound

from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component.event import objectEventNotify

from repoze.bfg.chameleon_zpt import render_template_to_response

from repoze.bfg.url import model_url
from repoze.bfg.traversal import model_path
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import effective_principals
from repoze.bfg.security import has_permission
from repoze.bfg.view import bfg_view

from formencode import Invalid as FormEncodeInvalid

from repoze.lemonade.content import create_content

from opencore.models.interfaces import IForum
from opencore.models.interfaces import IForumTopic
from opencore.models.interfaces import IForumsFolder

from opencore.events import ObjectModifiedEvent
from opencore.events import ObjectWillBeModifiedEvent

from opencore.models.interfaces import IComment
from opencore.models.interfaces import ICatalogSearch

from opencore.utils import get_layout_provider
from opencore.utils import find_interface
from opencore.utils import find_profiles
from opencore.utils import support_attachments
from opencore.utilities.image import thumb_url
from opencore.utilities.interfaces import IAppDates
from opencore.views.batch import get_catalog_batch_grid

from opencore.views.api import TemplateAPI

from opencore.views.people import PROFILE_THUMB_SIZE
from opencore.views.utils import convert_to_script
from opencore.views.utils import make_unique_name
from opencore.views.tags import set_tags
from opencore.views.tags import get_tags_client_data
from opencore.views.interfaces import IBylineInfo
from opencore.views.utils import fetch_attachments
from opencore.views.utils import upload_attachments
from opencore.views.utils import extract_description
from opencore.views.utils import comments_to_display
from opencore.views.validation import AddForumTopicSchema
from opencore.views.validation import State

log = logging.getLogger(__name__)

def titlesort(one, two):
    return cmp(one.title, two.title)

class ShowForumsView(object):
    _admin_actions = [
       # ('Add Forum', 'add_forum.html'),
        ]

    def __init__(self, context, request):
        self.context = context
        self.request = request
        layout_provider = get_layout_provider(self.context, self.request)
        self.layout = layout_provider('generic')

    def __call__(self):
        context = self.context
        request = self.request

        page_title = context.title
        api = TemplateAPI(context, request, page_title)
        appdates = getUtility(IAppDates)

        actions = []
        if has_permission('create', context, request):
            actions = self._admin_actions

        forums = list(context.values())
        forums.sort(titlesort)

        forum_data = []

        for forum in forums:
            D = {}
            D['title'] = forum.title
            D['url'] = model_url(forum, request)
            D['number_of_topics'] = number_of_topics(forum)
            D['number_of_comments'] = number_of_comments(forum, request)

            latest = latest_object(forum, request)

            _NOW = datetime.datetime.now()

            if latest:
                D['latest_activity_url'] = model_url(latest, request)
                D['latest_activity_link'] = getattr(latest, 'title', None)
                D['latest_activity_by'] = getattr(latest, 'creator', None)
                modified = getattr(latest, 'modified_date', _NOW)
                modified_str = appdates(modified, 'longform')
                D['latest_activity_at'] = modified_str
            else:
                D['latest_activity_url'] = None
                D['latest_activity_link'] = None
                D['latest_activity_by'] = None
                D['latest_activity_at'] = None

            forum_data.append(D)

        return render_template_to_response(
            'templates/show_forums.pt',
            api=api,
            actions=actions,
            forum_data = forum_data,
            layout = self.layout
            )

 
@bfg_view(for_=IForumsFolder, permission='view')
def show_forums_view(context, request):
    return ShowForumsView(context, request)()

def show_forum_view(context, request):

    page_title = context.title
    api = TemplateAPI(context, request, page_title)

    actions = []
    if has_permission('create', context, request):
        actions.append(('Add Forum Topic', 'add_forum_topic.html'))
    '''if has_permission('edit', context, request):
        actions.append(('Edit', 'edit.html'))
    if has_permission('delete', context, request):
        actions.append(('Delete', 'delete.html'))'''

    profiles = find_profiles(context)
    appdates = getUtility(IAppDates)

    topic_batch = get_topic_batch(context, request)
    topic_entries = topic_batch['entries']

    topics = []
    for topic in topic_entries:
        D = {}
        profile = profiles.get(topic.creator)
        posted_by = getattr(profile, 'title', None)
        date = appdates(topic.created, 'longform')
        D['url'] = model_url(topic, request)
        D['title'] = topic.title
        D['posted_by'] = posted_by
        D['date'] = date
        D['number_of_comments'] = len(topic['comments'])
        topics.append(D)

    # In the intranet side, the backlinks should go to the show_forums
    # view (the default)
    forums = context.__parent__
    backto = {
        'href': model_url(forums, request),
        'title': forums.title,
        }

    # Get a layout
    layout_provider = get_layout_provider(context, request)
    layout = layout_provider('generic')

    return render_template_to_response(
        'templates/show_forum.pt',
        api = api,
        actions = actions,
        title = context.title,
        topics = topics,
        batch_info = topic_batch,
        backto=backto,
        layout=layout,
        )

@bfg_view(for_=IForumTopic, permission='view')  
def show_forum_topic_view(context, request):
    post_url = model_url(context, request, "comments", "add_comment.html")
    page_title = context.title

    actions = []
    if has_permission('edit', context, request):
        actions.append(('Edit', 'edit.html'))
    if has_permission('delete', context, request):
        actions.append(('Delete', 'delete.html'))

    api = TemplateAPI(context, request, page_title)

    byline_info = getMultiAdapter((context, request), IBylineInfo)
    forum = find_interface(context, IForum)
    backto = {
        'href': model_url(forum, request),
        'title': forum.title,
        }

    # provide client data for rendering current tags in the tagbox
    client_json_data = dict(
        tagbox = get_tags_client_data(context, request),
        )

    # Get a layout
    layout_provider = get_layout_provider(context, request)
    layout = layout_provider('community')

    if support_attachments(context):
        attachments = fetch_attachments(context['attachments'], request)
    else:
        attachments = ()

    # enable imagedrawer for adding forum replies (comments)
    api.karl_client_data['text'] = dict(
            enable_imagedrawer_upload = True,
            )

    return render_template_to_response(
        'templates/show_forum_topic.pt',
        api=api,
        actions=actions,
        comments=comments_to_display(request),
        attachments=attachments,
        formfields=api.formfields,
        post_url=post_url,
        byline_info=byline_info,
        head_data=convert_to_script(client_json_data),
        backto=backto,
        layout=layout,
        comment_form={},
        )

def number_of_topics(forum):
    return len(forum)

def number_of_comments(forum, request):
    searcher = ICatalogSearch(forum)
    total, docids, resolver = searcher(
        interfaces=[IComment],
        path={'query': model_path(forum)},
        allowed={'query': effective_principals(request), 'operator': 'or'},
        )
    return total

def latest_object(forum, request):
    searcher = ICatalogSearch(forum)
    total, docids, resolver = searcher(
        sort_index='modified_date',
        interfaces={'query': [IForumTopic, IComment], 'operator':'or'},
        path={'query': model_path(forum)},
        allowed={'query': effective_principals(request), 'operator': 'or'},
        reverse=True)

    docids = list(docids)
    if docids:
        return resolver(docids[0])
    else:
        return None

def get_topic_batch(forum, request):
    return get_catalog_batch_grid(
        forum, request, interfaces=[IForumTopic], reverse=True,
        path={'query': model_path(forum)},
        allowed={'query': effective_principals(request), 'operator': 'or'},
        )

class AddForumTopicController(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
        layout_provider = get_layout_provider(self.context, self.request)
        self.layout = layout_provider('community')
        self.api = self.request.api
        self.api.page_title = 'Add Forum Topic'
      

    def form_defaults(self):
        defaults = {
            'title':'',
            'tags':[],
            'text':'',
            'attachments':[],
            }

        return defaults

    def __call__(self):
               
        if self.request.method == 'POST':
            post_data = self.request.POST
            log.debug('request.POST: %s' % post_data)
            try:
                # validate and convert
                self.api.formdata = AddForumTopicSchema.to_python(post_data,
                                             state=State(context=self.context))
            except FormEncodeInvalid, e:
                self.api.formdata = post_data
                raise ValidationError(self, **e.error_dict)
            else:
                return self.handle_submit(self.api.formdata)
        
        return self.make_response()

    def make_response(self):
                
        return render_template_to_response(
                'templates/add_forum_topic.pt', 
                api=self.api,
                actions=(),
                layout=self.layout
            )
        
        
    def handle_submit(self, converted):
        context = self.context
        request = self.request
      
        name = make_unique_name(context, converted['title'])
        creator = authenticated_userid(request)

        topic = create_content(IForumTopic,
            converted['title'],
            converted['text'],
            creator,
            )
        # todo: look further into calling extract_description as the text
        # has already been converted from html to text with validators.SafeInput
        if converted['text']:
            topic.description = extract_description(converted['text'])
        else:
            topic.description = converted['title']    
        context[name] = topic
      
        ''' Tags and attachments
        set_tags(context, request, converted['tags'])
        if support_attachments(topic):
            upload_attachments(converted['attachments'], topic['attachments'],
                               creator, request)'''

        location = model_url(topic, request)
        return HTTPFound(location=location)

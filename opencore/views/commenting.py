import urllib
import logging
from zope.component import getMultiAdapter
from webob.exc import HTTPFound
from webob.exc import HTTPExpectationFailed
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import has_permission
from repoze.bfg.url import model_url
from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.lemonade.content import create_content
from formencode import Invalid
from opencore.models.interfaces import IComment
from opencore.models.interfaces import IForumTopic
from opencore.views.validation import SafeInput
from opencore.views.utils import extract_description
from opencore.views.utils import upload_attachments
from opencore.views.api import TemplateAPI
from opencore.views.interfaces import IBylineInfo
from opencore.models.interfaces import IBlogEntry
from opencore.utils import support_attachments
from opencore.utils import find_interface
from opencore.utils import get_layout_provider
from opencore.views.utils import fetch_attachments
from opencore.models.interfaces import IProfile
from opencore.models.interfaces import ICommentsFolder

log = logging.getLogger(__name__)

def redirect_comments_view(context, request):
    # When deleting a comment, we get redirected to the parent.  It's
    # easier to implement another redirect than re-implement the
    # delete view.

    url = model_url(context.__parent__, request)
    status_message = request.GET.get('status_message', False)
    if status_message:
        msg = '?status_message=' + status_message
    else:
        msg = ''
    # avoid Unicode errors on webob.multidict or webob.descriptors.
    # only way to keep both happy from our end, since the redirect
    # complicates things
    location = url+msg
    location = location.encode('utf-8')
    return HTTPFound(location=location)

def show_comment_view(context, request):

    page_title = "Comment on " + context.title
    api = TemplateAPI(context, request, page_title)

    actions = []
    if has_permission('edit', context, request):
        actions.append(('Edit', 'edit.html'))
    if has_permission('delete', context, request):
        actions.append(('Delete', 'delete.html'))

    byline_info = getMultiAdapter((context, request), IBylineInfo)
    container = find_interface(context, IBlogEntry)
    if container is None:
        # Comments can also be in forum topics
        container = find_interface(context, IForumTopic)
    if container is None:
        # Comments can also be in profile
        container = find_interface(context, IProfile)    
    backto = {
        'href': model_url(container, request),
        'title': container.title,
        }

    # Get a layout
    layout_provider = get_layout_provider(context, request)
    layout = layout_provider('community')

    if support_attachments(context):
        attachments = fetch_attachments(context, request)
    else:
        attachments = ()

    return render_template_to_response(
        'templates/show_comment.pt',
        api=api,
        actions=actions,
        byline_info=byline_info,
        attachments=attachments,
        backto=backto,
        layout=layout,
        )


class AddCommentController(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        if self.request.method != 'POST':
            raise HTTPExpectationFailed(u'This is not a self-posting form. '
                                     u'It is submit only.')
        text = self.request.POST.get('comment.text', None)
        if find_interface(self.context, IBlogEntry):
            # the comments folder is in the parent 
            self.parent = self.context.__parent__
        else:
            # The comments folder is in the context, i.e. IForumTopic 
            # and IProfile if it contains testimonials as comments.
            self.parent = self.context
                
        if not text:
            return self.status_response('Please enter a comment')
        converted = {'attachments' : []}   # todo: when required
        try:
            converted['add_comment'] = SafeInput().to_python(text)   
        except Invalid, e:
            raise ValidationError(self, add_comment=str(e))     
        return self.handle_submit(converted)
    
    def status_response(self, msg):
        location = model_url(self.parent, self.request)
        if IComment.providedBy(self.context):
            # for comment replies we need the location of the real container 
            # like forum topic.
            location =  model_url(find_interface(self.context, IForumTopic), self.request)
        location = '%s?status_message=%s' % (location, urllib.quote(msg))
        return HTTPFound(location=location)
   
    def handle_submit(self, converted):
        context = self.context
        request = self.request
        parent = self.parent
        creator = authenticated_userid(request)
        log.debug('add_comment.html converted: %s, ctx: %s' % (str(converted),
                                                            self.context))
        comment = create_content(
            IComment,
            'Re: %s' % parent.title,
            converted['add_comment'],
            extract_description(converted['add_comment']),
            creator,
            )
        
        if not 'comments' in parent.keys():
            parent['comments'] = create_content(ICommentsFolder)
        comments = parent['comments']
        
        next_id = comments.next_id
        comments[next_id] = comment
       
        if support_attachments(comment):
            upload_attachments(converted['attachments'], comment,
                               creator, request)
        
        return self.status_response('Comment added') 
        

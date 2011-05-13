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

import urllib
import logging
from zope.component import getMultiAdapter
from webob.exc import HTTPFound
from webob.exc import HTTPExpectationFailed
from repoze.bfg.security import authenticated_userid
from repoze.bfg.security import has_permission
from repoze.bfg.url import model_url
from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.exceptions import ExceptionResponse
from repoze.lemonade.content import create_content
from opencore.models.interfaces import IComment
from opencore.models.interfaces import IForumTopic
from opencore.views.validation import safe_html
from opencore.views.utils import extract_description
from opencore.views.utils import upload_attachments
from opencore.views.api import TemplateAPI
from opencore.views.interfaces import IBylineInfo
from opencore.models.interfaces import IBlogEntry
from opencore.utils import support_attachments
from opencore.utils import find_interface
from opencore.utils import find_supported_interface
from opencore.utils import get_layout_provider
from opencore.views.utils import fetch_attachments
from opencore.models.interfaces import IProfile
from opencore.models.interfaces import ICommunity
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
    api = request.api
    api.page_title = page_title
    

    actions = []
    if has_permission('edit', context, request):
        actions.append(('Edit', 'edit.html'))
    if has_permission('delete', context, request):
        actions.append(('Delete', 'delete.html'))

    byline_info = getMultiAdapter((context, request), IBylineInfo)
    container = find_supported_interface(context, api.supported_comment_interfaces())  
    if not container:
        err_msg = 'unsupported interface for show_comment_view found for ' \
          'context: %s' % context  
        log.warn(err_msg)          
        exception_response = ExceptionResponse(err_msg)
        exception_response.status = '500 Internal Server Error'
        return exception_response
          
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
        converted['add_comment'] = safe_html(text)   
        return self.handle_submit(converted)
    
    def status_response(self, msg):
        location = model_url(self.parent, self.request)
        if IComment.providedBy(self.context):
            # for comment replies we need the location of the real container 
            # like forum topic or profile or community
            log.debug('commenting status_response: reply context=%s, grandparent=%s' % (self.context, self.parent.__parent__))
            location = model_url(self.parent.__parent__, self.request)
            
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
            parent.title,
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
        

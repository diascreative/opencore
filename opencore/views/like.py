import logging
from urllib import quote
from zope.component.event import objectEventNotify
from zope.component import getMultiAdapter
from webob.exc import HTTPFound
from repoze.bfg.security import authenticated_userid
from repoze.bfg.url import model_url
from repoze.lemonade.interfaces import IContent
from repoze.lemonade.content import create_content
from opencore.events import ObjectModifiedEvent
from opencore.models.interfaces import ILike

log = logging.getLogger(__name__)

class AlreadyLiked(ValueError):
    pass
   
def like(context, request):
    creator = authenticated_userid(request)
    try:
        if 'likes' not in context.__dict__:
            context.likes = create_content(ILike, creator)
        else:
            if context.likes.has_user(creator):
                raise AlreadyLiked()
            context.likes.add(creator)  
                 
        objectEventNotify(ObjectModifiedEvent(context))
        msg = 'You like %s' % context.title      
           
    except AlreadyLiked, e:
        msg = 'You already like %s' % context.title 
    
    location = '%s?status_message=%s' % (model_url(context, request), quote(msg))     
    return HTTPFound(location=location)
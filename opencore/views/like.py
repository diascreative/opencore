# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz.org
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
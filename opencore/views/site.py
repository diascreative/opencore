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

"""Publish static resources under /static/"""

import os
import re

from webob.exc import HTTPFound

from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.url import model_url
from repoze.bfg.view import static

from opencore.views.utils import get_user_home
from opencore.views.api import TemplateAPI
import logging

log = logging.getLogger(__name__) 

here = os.path.abspath(os.path.dirname(__file__))

# five year expires time
static_view = static('static', cache_max_age=157680000)

version_match = re.compile(r'^r-?\d+$').match
# version number is "r" plus an integer (possibly negative)

def versioning_static_view(context, request):
    # if the first element in the subpath is the version number, strip
    # it out of the subpath (see views/api.py static_url)
    subpath = request.subpath
    if subpath and version_match(subpath[0]):
        request.subpath = subpath[1:]
    return static_view(context, request)

def site_view(context, request):
    home, extra_path = get_user_home(context, request)
    location=model_url(home, request, *extra_path)
    log.info('site_view location=%s' % location)
    return HTTPFound(location=model_url(home, request, *extra_path))

class StaticRootFactory(object):
    def __init__(self, environ):
        pass

def not_found(context, request):
    api = request.api
    api.page_title = 'Page Not Found!'
   
    response = render_template_to_response(
        'templates/404.pt',
        api=api
        )
    response.status = '404 Not Found'
    
    return response
   

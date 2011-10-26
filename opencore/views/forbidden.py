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

from repoze.bfg.chameleon_zpt import render_template_to_response
from repoze.bfg.url import model_url

from opencore.views.api import TemplateAPI
from opencore.utils import find_site
from webob.exc import HTTPFound

def forbidden(context, request):
    # Note context is repoze.bfg.exceptions.Forbidden
    site = find_site(request.context)
    environ = request.environ
    referrer = environ.get('HTTP_REFERER', '')
       
    if 'repoze.who.identity' in environ:
        # the user is authenticated but he is not allowed to access this
        # resource
        api = TemplateAPI(request.context, request, 'Forbidden')
        response =  render_template_to_response(
            'templates/forbidden.pt',
            api=api,
            login_form_url = model_url(site, request, 'login.html'),
            homepage_url = model_url(site, request),
            )
        response.status = '403 Forbidden'
        return response
    elif '/login.html' in referrer:
        url = request.url
        # this request came from a user submitting the login form
        login_url = model_url(site, request, 'login.html',
                              query={'reason':'Bad username or password',
                                     'came_from':url})
        return HTTPFound(location=login_url)
    else:
        # the user is not authenticated and did not come in as a result of
        # submitting the login form
        url = request.url
        query = {'came_from':url}
        while url.endswith('/'):
            url = url[:-1]
        if url != request.application_url: # if request isnt for homepage
            query['reason'] = 'Not logged in'
        login_url = model_url(site, request, 'login.html', query=query)
        return HTTPFound(location=login_url)

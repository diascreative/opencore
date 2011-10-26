# Copyright (C) 2010-2011 Large Blue
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

import os
from webob import Request, Response
from chameleon.zpt.loader import TemplateLoader

DEFAULT_COOKIE_LIFETIME = 10 * 365 * 24 * 60 * 60 # 10 years

class GatewayMiddleware(object):
    def __init__(self, app, global_conf, password, cookie_name, cookie_value, domain, lifetime=DEFAULT_COOKIE_LIFETIME, default_message=''):
        self.app = app
        self.password = password
        self.cookie_name = cookie_name
        self.cookie_value = cookie_value
        self.domain = domain
        self.lifetime = lifetime
        self.default_message = default_message
        self.loader = TemplateLoader(os.path.dirname(__file__))
    
    def __call__(self, environ, start_response):
        request = Request(environ)
        password = request.params.get('password', None)

        if request.cookies.get(self.cookie_name, None) == self.cookie_value:
            return self.app(environ, start_response)

        elif password == self.password:
            res = request.get_response(self.app)
            res.set_cookie(self.cookie_name, self.cookie_value, max_age=self.lifetime, path='/',
                           domain=self.domain)
            return res(environ, start_response)

        else:
            template = self.loader.load('form.pt')
            res = Response(content_type='text/html', charset='utf8', body=template.render())
            return res(environ, start_response)

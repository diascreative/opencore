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

from repoze.bfg.compat import json

def jsonp_renderer_factory(name):
    """ Configure this factory under the name `.jsonp` so that the
        callback can be defined before the suffix.
    """
    def _render(value, system):
        request = system.get('request')
        callback_key = 'callback'
        callback = None
        if request is not None:
            if not hasattr(request, 'response_content_type'):
                request.response_content_type = 'application/json'
            if 'jsonp_callback_key' in request.params:
                callback_key = request.params['jsonp_callback_key']

            callback = request.params.get(callback_key)

        res = json.dumps(value)
        if callback:
            res = '%s(%s);' % (callback, res)
        return res
    return _render

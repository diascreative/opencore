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

"""
    A repoze.who plugin to support api-key requests, where
    a small number of keys are contained in the 

"""
from urlparse import parse_qs

class APIKeyPlugin(object):

    def __init__(self, key_name, keys='', user_name=''):
        self.key_name = key_name.strip()
        self.valid_keys = [v.strip() for v in keys.split(',')]
        self.user_name = user_name.strip()

    def identify(self, environ):
        this_key = self._extract_key(environ)
        if this_key and this_key in self.valid_keys:
            return {'repoze.who.userid' : self.user_name}
        else:
            return None

    def forget(self, environ, identity):
        return None

    def remember(self, environ, identity):
        return None
    
    def _extract_key(self, environ):
        try:
            return parse_qs(environ['QUERY_STRING'])[self.key_name][0]
        except Exception:
            return None

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, id(self))

def make_plugin(key_name=None, keys='', user_name=''):
    return APIKeyPlugin(key_name, keys, user_name)

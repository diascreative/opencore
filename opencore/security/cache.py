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

from zope.interface import implements
from repoze.bfg.location import lineage
from repoze.bfg.security import Everyone
from opencore.security.interfaces import IACLPathCache
from opencore.security.policy import AllPermissionsList

class ACLPathCache(object):
    implements(IACLPathCache)
    def __init__(self):
        self._index = {}

    def _getPath(self, model):
        rpath = []
        for location in lineage(model):
            if location.__name__ is None:
                break
            rpath.insert(0, location.__name__)
        return tuple(rpath)

    def clear(self, model=None):
        """ See IACLPathCache.
        """
        if model is None:
            self._index.clear()
            return
        path = self._getPath(model)
        lpath = len(path)
        purged = [x for x in self._index.keys() if x[:lpath] == path]
        for key in purged:
            del self._index[key]

    def index(self, model):
        """ See IACLPathCache.
        """
        for obj in lineage(model):
            acl = getattr(obj, '__acl__', None)
            if acl is not None:
                self._index[self._getPath(obj)] = acl[:]

    def lookup(self, model, permission=None):
        """ See IACLPathCache.
        """
        aces = []
        for obj in lineage(model):
            path = self._getPath(obj)
            acl = self._index.get(path)
            if acl is None:
                acl = getattr(obj, '__acl__', ())
                if acl:
                    self._index[path] = acl
            if permission is not None:
                acl = [x for x in acl
                        if x[2] == permission
                            or isinstance(x[2], AllPermissionsList)]
            aces.extend(acl)
            if [x for x in acl if x[1] is Everyone]:
                break
        return aces

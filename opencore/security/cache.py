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

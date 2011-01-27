from zope.interface import Interface

class IACLPathCache(Interface):
    """ Utility:  maps an object's path to the nodes "above" it having ACLs.
    """
    def clear(model=None):
        """ Clear the cache for 'model' and any descendants.

            o If 'model' is None, clear the whole cache.
        """

    def index(model):
        """ Index model's ACL, if it has one.

            o If "DENY ALL" not in the ACL, recurse to model's __parent__.
        """

    def lookup(model, permission=None):
        """ Return the ACEs for 'model' relevant to 'permission'.

            o If 'permission' is None, return all ACEs.

            o Crawl the parent chain until we get to the root, or until we
              find an allow or a deny for the given permission to Everyone.

            o If cache is populated for any node, use that value.

            o Populate the cache as we search.
        """


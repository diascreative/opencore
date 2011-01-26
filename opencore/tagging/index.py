import BTrees
from zope.interface import implements
from repoze.catalog.interfaces import ICatalogIndex


class TagIndex(object):
    """ An index that defers to the tagging engine.

        This index does not actually store anything.  It queries the
        site tagging engine.  It relies on the fact that the catalog and
        tagging engine use the same document map, so the docids match.
    """
    implements(ICatalogIndex)
    family = BTrees.family32

    def __init__(self, site):
        self.site = site

    def index_doc(self, docid, value):
        # the tagging engine handles this
        pass

    def unindex_doc(self, docid):
        # the tagging engine handles this
        pass

    def reindex_doc(self, docid, obj):
        # the tagging engine handles this
        pass

    def clear(self):
        # the tagging engine handles this
        pass

    def apply_intersect(self, query, docids):
        """ Run the query implied by query, and return query results
            intersected with the ``docids`` set that is supplied.  If
            ``docids`` is None, return the bare query results.
        """
        result = self.apply(query)
        if docids is None:
            return result
        return self.family.IF.weightedIntersection(result, docids)[1]

    def apply(self, query):
        if not isinstance(query, dict):
            query = {'query': query}
        return self.search(**query)

    def search(self, query, operator='and', users=None, community=None):
        if isinstance(query, basestring):
            query = [query]

        if operator == 'or':
            res = self.site.tags.getItems(
                tags=query, users=users, community=community)
        elif operator == 'and':
            sets = []
            for tag in query:
                sets.append(self.site.tags.getItems(
                    tags=[tag], users=users, community=community))
            if sets:
                res = reduce(set.intersection, sets)
            else:
                res = set()
        else:
            raise TypeError('Tag index only supports `and` and `or` '
                'operators, not `%s`.' % operator)

        return self.family.IF.Set(res)

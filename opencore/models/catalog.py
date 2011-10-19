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

import os
import sys
import time
import cPickle

import transaction

from zope.event import notify
from zope.interface import implements
from zope.component import queryUtility

from repoze.bfg.traversal import find_model
from repoze.catalog.catalog import Catalog
from repoze.catalog.interfaces import ICatalog
from repoze.lru import LRUCache

from opencore.models.interfaces import ICatalogQueryEvent
from opencore.models.interfaces import ICatalogSearchCache
from opencore.utils import find_site

from BTrees.Length import Length

LARGE_RESULT_SET = 500

class CachingCatalog(Catalog):
    implements(ICatalog)

    os = os # for unit tests
    generation = None # b/c

    def __init__(self):
        super(CachingCatalog, self).__init__()
        self.generation = Length(0)

    def clear(self):
        self.invalidate()
        super(CachingCatalog, self).clear()

    def index_doc(self, *arg, **kw):
        self.invalidate()
        super(CachingCatalog, self).index_doc(*arg, **kw)

    def unindex_doc(self, *arg, **kw):
        self.invalidate()
        super(CachingCatalog, self).unindex_doc(*arg, **kw)

    def reindex_doc(self, *arg, **kw):
        self.invalidate()
        super(CachingCatalog, self).reindex_doc(*arg, **kw)

    def __setitem__(self, *arg, **kw):
        self.invalidate()
        super(CachingCatalog, self).__setitem__(*arg, **kw)

    def search(self, *arg, **kw):
        use_cache = True

        if 'use_cache' in kw:
            use_cache = kw.pop('use_cache')

        if 'NO_CATALOG_CACHE' in self.os.environ:
            use_cache = False

        if 'tags' in kw:
            # The tags index changes without invalidating the catalog,
            # so don't cache any query involving the tags index.
            use_cache = False

        if not use_cache:
            return self._search(*arg, **kw)

        cache = queryUtility(ICatalogSearchCache)

        if cache is None:
            return self._search(*arg, **kw)

        key = cPickle.dumps((arg, kw))

        generation = self.generation

        if generation is None:
            generation = Length(0)

        genval = generation.value

        if (genval == 0) or (genval > cache.generation):
            # an update in another process requires that the local cache be
            # invalidated
            cache.clear()
            cache.generation = genval

        if cache.get(key) is None:
            num, docids = self._search(*arg, **kw)

            # We don't cache large result sets because the time it takes to
            # unroll the result set turns out to be far more time than it
            # takes to run the search. In a particular instance using OSI's
            # catalog a search that took 0.015s but returned nearly 35,295
            # results took over 50s to unroll the result set for caching,
            # significantly slowing search performance.
            if num > LARGE_RESULT_SET:
                return num, docids

            # we need to unroll here; a btree-based structure may have
            # a reference to its connection
            docids = list(docids)
            cache.put(key, (num, docids))

        return cache.get(key)

    def _search(self, *arg, **kw):
        start = time.time()
        res = super(CachingCatalog, self).search(*arg, **kw)
        duration = time.time() - start
        notify(CatalogQueryEvent(self, kw, duration, res))
        return res

    def invalidate(self):
        # Increment the generation; this tells *another process* that
        # its catalog cache needs to be cleared
        generation = self.generation

        if generation is None:
            generation = self.generation = Length(0)

        if generation.value >= sys.maxint:
            # don't keep growing the generation integer; wrap at sys.maxint
            self.generation.set(0)
        else:
            self.generation.change(1)

        # Clear the cache for *this process*
        cache = queryUtility(ICatalogSearchCache)
        if cache is not None:
            cache.clear()
            cache.generation = self.generation.value

# the ICatalogSearchCache component (wired in via ZCML)
cache = LRUCache(1000)
cache.generation = 0


class CatalogQueryEvent(object):
    implements(ICatalogQueryEvent)
    def __init__(self, catalog, query, duration, result):
        self.catalog = catalog
        self.query = query
        self.duration = duration
        self.result = result


##TODO: move to utilities?
def reindex_catalog(context, path_re=None, commit_interval=200, dry_run=False,
                    output=None, transaction=transaction, indexes=None):

    def commit_or_abort():
        if dry_run:
            output and output('*** aborting ***')
            transaction.abort()
        else:
            output and output('*** committing ***')
            transaction.commit()

    site = find_site(context)
    catalog = site.catalog

    output and output('updating indexes')
    site.update_indexes()
    commit_or_abort()

    if indexes is not None:
        output and output('reindexing only indexes %s' % str(indexes))

    i = 1
    for path, docid in catalog.document_map.address_to_docid.items():
        if path_re is not None and path_re.match(path) is None:
            continue
        output and output('reindexing %s' % path)
        try:
            model = find_model(context, path)
        except KeyError:
            output and output('error: %s not found' % path)
            continue

        if indexes is None:
            catalog.reindex_doc(docid, model)
        else:
            for index in indexes:
                catalog[index].reindex_doc(docid, model)
        if i % commit_interval == 0:
            commit_or_abort()
        i+=1
    commit_or_abort()

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


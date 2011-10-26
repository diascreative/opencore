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

from zope.interface import Attribute
from zope.interface import Interface

class IBootstrapper(Interface):
    """ Bootstraps a Karl instance by populating the ZODB with an initialized site
        structure.
    """
    def __call__(root):
        """ Creates a Karl site in the ZODB root with the name 'site'.
        """

class IInitialData(Interface):
    """ Provides data used to initialize a Karl site.

        TODO: Extend interface to require attributes referenced in
              opencore.bootstrap.bootstrap.populate
    """

class IInitialOfficeData(Interface):
    """ Provides data used to initialize offices.
    """

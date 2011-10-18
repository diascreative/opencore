# Copyright (C) 2008-2009 Open Society Institute
#               !!! The original copyright holder !!!
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
from zope.component.interfaces import IObjectEvent

class IObjectWillBeModifiedEvent(IObjectEvent):
    """ An event type sent before an object is modified  """
    object = Attribute('The object that will be modified')

class IObjectModifiedEvent(IObjectEvent):
    """ An event type sent after an object is modified """
    object = Attribute('The object which was modified')


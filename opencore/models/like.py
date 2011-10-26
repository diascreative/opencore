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

import logging
from zope.interface import implements
from persistent import Persistent
from appendonly import AppendStack
from opencore.models.interfaces import ILike

log = logging.getLogger(__name__)

class Like(Persistent):
    '''
    Like content. 
    '''
    implements(ILike)
    
    def __init__(self, user=None):
        self.users = AppendStack()
        self._count = 0
        if user:
            self.users.push(user)
            self._count += 1
        
    def __len__(self):
        return len(list(self.users))
    
    def count(self):
        return self._count 
    
    def add(self, user):  
        self.users.push(user)
        self._count += 1
        
    def has_user(self, user): 
        for x,y,u in self.users:
            log.debug('%s=%s' % (user, u))
            if user == u:
                return True  
        return False    
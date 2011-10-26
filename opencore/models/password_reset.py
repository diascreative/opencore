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


# stdlib
from datetime import datetime, timedelta

# Zope
from zope.interface import implements

# opencore
from opencore.models.interfaces import IPasswordRequestRequest

REQUEST_VALIDITY_HOURS = 24

class PasswordRequestRequest(object):
    implements(IPasswordRequestRequest)
    
    def __init__(self, request_id, email):
        self.request_id = request_id
        self.email = email
        self.valid_from, self.valid_to = self.get_valid_from_to()
        
    def get_valid_from_to(self):
        from_ = datetime.utcnow()
        to = from_ + timedelta(hours=REQUEST_VALIDITY_HOURS)
        return from_, to
    
    def __repr__(self):
        return '<%s at %s, request_id=[%s] valid_from=[%s] valid_to=[%s]>' % (
            self.__class__.__name__, hex(id(self)), self.request_id, 
            self.valid_from, self.valid_to)
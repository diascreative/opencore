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
import sqlalchemy as sa
from opencore.models import sql

log = logging.getLogger(__name__)

# SQLAlchemy database engine. set within __init__. 
sqlEngine = None

# SQLAlchemy session manager. set within __init__. 
sqlSession = None

class RDBMSStore(object):
        
    def view_count(self, path):
        return self.execute(sql.view_count, path=path).fetchall()
                      
    def execute(self, sqlText, **kwargs):
        assert(sqlSession)
        assert(sqlText)
        return sqlSession().execute(sa.text(sqlText), kwargs)  
  

  
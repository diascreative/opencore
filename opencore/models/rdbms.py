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
  

  
import sqlalchemy as sa
from sqlalchemy import orm
import sqlalchemy.pool as pool
from opencore.models import rdbms

def init_rdbms(engine):
    """Call me before using any RDBMSStore class in the model."""
    sm = orm.sessionmaker(autocommit=True, bind=engine)
    rdbms.sqlEngine = engine
    rdbms.sqlSession = orm.scoped_session(sm)
    sqlEngine = engine
    sqlSession = orm.scoped_session(sm)
    assert(sqlEngine)
    assert(sqlSession)
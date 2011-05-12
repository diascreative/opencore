
# stdlib
import uuid, datetime

# Repoze
from repoze.bfg import testing

# Zope
from zope.interface import implements

# opencore
from opencore.models.interfaces import ICommunityInfo, ITagQuery

class DummyAPI(object):
    def __init__(self):
        self.page_title = None

    def view_count(self, *args_ignored, **kwargs_ignored):
        pass

    def view_count(self, *args_ignored, **kwargs_ignored):
        pass

    def like_count(self, *args_ignored, **kwargs_ignored):
        pass
    
class DummyAdapter(object):
    implements(ICommunityInfo, ITagQuery)
    def __init__(self, context, request):
        self.name = context.__name__
        self.tagswithcounts = []
        self.docid = None
        self.url = 'http://dummyurl.example.com'
        
class DummyContext(testing.DummyModel):
    def __init__(self, *args, **kwargs):
        testing.DummyModel.__init__(self, *args, **kwargs)
        self.projects = kwargs.get('projects', [])
        self._test_stories = kwargs.get('_test_stories', [])
        self.country = 'PL'
        self.phase = 'hear'
        self.websites = None
        self.created = datetime.datetime.now()
        self.communities_name = None
        self.creator = 'admin'
        self.description = 'dummy description'
        self.websites = ['http://example.com/1', 'http://example.com/2']
        self.title = uuid.uuid4().hex

    def get(self, *args_ignored, **kwargs_ignored):
        return {}
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
import uuid, datetime

# Repoze
from repoze.bfg import testing

# Zope
from zope.interface import implements

# opencore
from opencore.models.interfaces import ICommunityInfo, ITagQuery
from opencore.testing import DummyProfile

class DummyAPI(object):
    
    userid = 'auser'
    
    def __init__(self):
        self.page_title = None
        self._profile = None
        self.people_url = ''

    def view_count(self, *args_ignored, **kwargs_ignored):
        pass

    def view_count(self, *args_ignored, **kwargs_ignored):
        pass

    def like_count(self, *args_ignored, **kwargs_ignored):
        pass

    def find_profile(self, uid):
        if self._profile:
            return self._profile
        
        return DummyProfile()
    
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

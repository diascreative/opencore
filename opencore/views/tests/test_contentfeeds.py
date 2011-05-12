
# stdlib
import unittest
from datetime import datetime

# Zope
from zope.interface import implements
from zope.interface import Interface
from zope.interface import taggedValue

# Repoze
from repoze.bfg import testing
from repoze.bfg.testing import cleanUp

# testfixtures
from testfixtures import Replacer

# opencore
from opencore.models.adapters import ProfileDict
from opencore.models.interfaces import IProfileDict
from opencore.views.tests import DummyAPI, DummyContext

def _checkCookie(request_or_response, filterby):
    from opencore.views.contentfeeds import _FILTER_COOKIE
    header = ('Set-Cookie',
              '%s=%s; Path=/' % (_FILTER_COOKIE, filterby))
    headerlist = getattr(request_or_response, 'headerlist', None)
    if headerlist is None:
        headerlist = getattr(request_or_response, 'response_headerlist')
    assert header in headerlist
    
class ProfileFeedViewTestCase(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.contentfeeds import profile_feed_view
        return profile_feed_view(context, request)
    
    def test_profile_feed_view_returns_profile_and_actions(self):
        
        def _dummy(*args_ignored, **kwargs_ignored):
            return []

        def _dummy2(*args_ignored, **kwargs_ignored):
            class _Dummy(object):
                __name__ = 'dummy'
                communities_name = __name__

                def get_by_id(self, *args_ignored, **kwargs_ignored):
                    return {'groups': []}

                get = get_by_id

            return _Dummy()
            
        with Replacer() as r:
            r.replace('opencore.utilities.image.thumb_url', _dummy)
            r.replace('opencore.views.people.thumb_url', _dummy)
            r.replace('opencore.models.adapters.thumb_url', _dummy)
            r.replace('opencore.utils.find_users', _dummy2)
            r.replace('opencore.views.people.find_users', _dummy2)
            r.replace('opencore.utils.find_root', _dummy2)
            r.replace('opencore.views.utils.comments_to_display', _dummy2)
            r.replace('opencore.views.communities.get_preferred_communities', _dummy)
            r.replace('opencore.views.people.get_preferred_communities', _dummy)
            r.replace('opencore.views.people.comments_to_display', _dummy2)
            
            api = DummyAPI()
            testing.registerUtility(ProfileDict(), IProfileDict, 'profile-details')
            
            context = DummyContext()
            request = testing.DummyRequest()
            request.api = api
            result = self._callFUT(context, request)

            profile = result.get('profile', False)
            self.assertTrue(profile)
            self.assertEquals(profile['title'], context.title)
            
            self.assertTrue(len(result.get('actions', [])) > 0)
            
    
class NewestFeedItemsViewTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.contentfeeds import newest_feed_items
        return newest_feed_items(context, request)

    def test_without_parameter(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        self.assertEqual(last_gen, 1)
        self.assertEqual(last_index, 2)
        self.assertEqual(earliest_gen, 1)
        self.assertEqual(earliest_index, 2)
        self.assertEqual(len(feed_items), 1)
        self.assertEqual(feed_items[0]['content_type'], 'Blog Entry')
        self.assertTrue('allowed' not in feed_items[0])
        self.assertEqual(feed_items[0]['timeago'], '2010-07-14T12:47:12Z')

    def test_filter_cookie_empty_no_param(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        _checkCookie(request, '')

    def test_filter_cookie_empty(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        request.params = {
            'filter': '',
            }
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        _checkCookie(request, '')

    def test_filter_cookie_mycommunities(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        request.params = {
            'filter': 'mycommunities',
            }
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        _checkCookie(request, 'mycommunities')

    def test_filter_cookie_mycontent(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        request.params = {
            'filter': 'mycontent',
            }
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        _checkCookie(request, 'mycontent')

    def test_filter_cookie_profile(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        request.params = {
            'filter': 'profile:phred',
            }
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        _checkCookie(request, 'profile:phred')

    def test_filter_cookie_community(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        request.params = {
            'filter': 'community:bhedrock',
            }
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        _checkCookie(request, 'community:bhedrock')

    def test_with_parameter_results(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        request.params = {
            'newer_than': '0:0',
            }
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        self.assertEqual(last_gen, 0)
        self.assertEqual(last_index, 1)
        self.assertEqual(earliest_gen, 0)
        self.assertEqual(earliest_index, 0)
        self.assertEqual(len(feed_items), 2)
        self.assertEqual(feed_items[0]['content_type'], 'Blog Entry')
        self.assertTrue('allowed' not in feed_items[0])
        self.assertEqual(feed_items[0]['timeago'], '2010-07-13T12:47:12Z')

    def test_with_parameter_noresults(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEventsEmpty()
        request.params = {
            'newer_than': '0:0',
            }
        (last_gen, last_index, earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        self.assertEqual(last_gen, 0)
        self.assertEqual(last_index, 0)
        self.assertEqual(earliest_gen, 0)
        self.assertEqual(earliest_index, 0)
        self.assertEqual(len(feed_items), 0)

class OlderFeedItemsViewTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.contentfeeds import older_feed_items
        return older_feed_items(context, request)

    def test_without_parameter(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        (earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        self.assertEqual(earliest_gen, -1L)
        self.assertEqual(earliest_index, -1)
        self.assertEqual(len(feed_items), 0)

    def test_with_parameter_results(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEvents()
        request.params = {
            'older_than': '0:5',
            }
        (earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        self.assertEqual(earliest_gen, 2)
        self.assertEqual(earliest_index, 3)
        self.assertEqual(len(feed_items), 1)
        self.assertEqual(feed_items[0]['content_type'], 'Community')
        self.assertTrue('allowed' not in feed_items[0])
        self.assertEqual(feed_items[0]['timeago'], '2010-07-15T13:47:12Z')

    def test_with_parameter_noresults(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        context.events = DummyEventsEmpty()
        request.params = {
            'older_than': '0:5',
            }
        (earliest_gen, earliest_index,
            feed_items) = self._callFUT(context, request)
        self.assertEqual(earliest_gen, 0)
        self.assertEqual(earliest_index, 5)
        self.assertEqual(len(feed_items), 0)

class DummyEvents:
    def checked(self, principals, created_by):
        results = [(1, 2, {'foo': 'bam', 'allowed': ['phred', 'bharney'],
                   'content_creator': 'phred', 'content_type': 'Blog Entry',
                   'timestamp': datetime(2010, 7, 14, 12, 47, 12),
                   'context_url': None})]
        return results

    def newer(self, gen, index, principals, created_by):
        results = [(0, 1, {'foo': 'bam', 'allowed': ['phred', 'bharney'],
                   'content_creator': 'phred', 'content_type': 'Blog Entry',
                   'timestamp': datetime(2010, 7, 13, 12, 47, 12)}),
                   (0, 0, {'foo': 'bar', 'allowed': ['phred', 'bharney'],
                    'userid': 'phred', 'content_type': 'Community',
                   'timestamp': datetime(2010, 7, 13, 13, 47, 12)})]
        return results

    def older(self, gen, index, principals, created_by):
        results = [(2, 3, {'foo': 'bar', 'allowed': ['phred', 'bharney'],
                    'userid': 'phred', 'content_type': 'Community',
                   'timestamp': datetime(2010, 7, 15, 13, 47, 12),
                   'context_url': '/foo'})]
        return results

class DummyEventsEmpty:
    def checked(self, principals, created_by):
        results = []
        return results

    def newer(self, gen, index, principals, created_by):
        results = []
        return results

    def older(self, gen, index, principals, created_by):
        results = []
        return results


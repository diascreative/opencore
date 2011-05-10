import unittest

from repoze.bfg import testing
from zope.interface import implements
from zope.interface import Interface
from zope.interface import taggedValue
from repoze.bfg.testing import cleanUp

class JQueryLivesearchViewTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.search import jquery_livesearch_view
        return jquery_livesearch_view(context, request)

    def test_no_parameter(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        testing.registerAdapter(DummySearch, (Interface),
                                ICatalogSearch)
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '400 Bad Request')


    def test_with_parameter_noresults(self):
        def dummy_factory(context, request, term):
            def results():
                return 0, [], None
            return results
        from repoze.lemonade.testing import registerListItem
        from opencore.models.interfaces import IGroupSearchFactory
        registerListItem(IGroupSearchFactory, dummy_factory, 'dummy1',
                         title='Dummy1', sort_key=1)
        context = testing.DummyModel()
        request = testing.DummyRequest()
        dummycontent = testing.DummyModel()
        request.params = {
            'val': 'somesearch',
            }
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '200 OK')
        from simplejson import loads
        results = loads(response.body)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['rowclass'], 'showall')
        self.assertEqual(results[0]['header'], '')
        self.assertEqual(results[0]['title'], 'Show All')
        self.assertEqual(results[1]['header'], 'Dummy1')
        self.assertEqual(results[1]['title'], 'No Result')

    def test_with_parameter_withresults(self):
        def dummy_factory1(context, request, term):
            pass
        def dummy_factory2(context, request, term):
            def results():
                return 1, [1], lambda x: testing.DummyModel(title='yo')
            return results
        from repoze.lemonade.testing import registerListItem
        from opencore.models.interfaces import IGroupSearchFactory
        registerListItem(IGroupSearchFactory, dummy_factory1, 'dummy1',
                         title='Dummy1', sort_key=1)
        registerListItem(IGroupSearchFactory, dummy_factory2, 'dummy2',
                         title='Dummy2', sort_key=2)
        context = testing.DummyModel()
        request = testing.DummyRequest()
        dummycontent = testing.DummyModel()
        request.params = {
            'val': 'somesearch',
            }
        response = self._callFUT(context, request)
        self.assertEqual(response.status, '200 OK')
        from simplejson import loads
        results = loads(response.body)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['rowclass'], 'showall')
        self.assertEqual(results[0]['header'], '')
        self.assertEqual(results[0]['title'], 'Show All')
        self.assertEqual(results[1]['header'], 'Dummy2')
        self.assertEqual(results[1]['title'], 'yo')
        self.assertEqual(response.content_type, 'application/x-json')


class SearchResultsViewTests(unittest.TestCase):
    def setUp(self):
        cleanUp()
        testing.registerDummyRenderer('opencore.views:templates/generic_layout.pt')
        testing.registerDummyRenderer(
            'opencore.views:templates/community_layout.pt')

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.search import SearchResultsView
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        view = SearchResultsView(context, request)
        view.type_to_result_dict[DummyContent] = 'test-content'
        return view()

    def test_no_searchterm(self):
        from webob.multidict import MultiDict
        context = testing.DummyModel()
        request = testing.DummyRequest(params=MultiDict())
        from opencore.models.interfaces import ICatalogSearch
        testing.registerAdapter(DummyEmptySearch, (Interface),
                                ICatalogSearch)
        result = self._callFUT(context, request)
        #self.assertEqual(result.status, '404 Not Found')

    def test_bad_kind(self):
        from webob.multidict import MultiDict
        context = testing.DummyModel()
        request = testing.DummyRequest(
            params=MultiDict({'kind':'unknown', 'body':'yo'}))
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from webob.exc import HTTPBadRequest
        testing.registerAdapter(DummyEmptySearch, (Interface),
                                ICatalogSearch)
        self.assertRaises(HTTPBadRequest, self._callFUT, context, request)

    def test_none_kind(self):
        from webob.multidict import MultiDict
        context = testing.DummyModel()
        request = testing.DummyRequest(params=MultiDict({'body':'yo'}))
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from repoze.lemonade.testing import registerContentFactory
        registerContentFactory(DummyContent, IDummyContent)
        testing.registerAdapter(DummySearch, (Interface),
                                ICatalogSearch)
        result = self._callFUT(context, request)
        self.assertEqual(result['terms'], ['yo'])
        self.assertEqual(len(result['results']), 1)

    def test_known_kind(self):
        from webob.multidict import MultiDict
        from opencore.models.interfaces import IGroupSearchFactory
        from repoze.lemonade.testing import registerContentFactory
        from zope.interface import Interface
        content = DummyContent()
        def search_factory(*arg, **kw):
            return DummySearchFactory(content)
        testing.registerUtility(
            search_factory, IGroupSearchFactory, name='People')
        context = testing.DummyModel()
        request = testing.DummyRequest(
            params=MultiDict({'body':'yo', 'kind':'People'}))
        from opencore.models.interfaces import ICatalogSearch
        registerContentFactory(DummyContent, IDummyContent)
        testing.registerAdapter(DummySearch, (Interface),
                                ICatalogSearch)
        result = self._callFUT(context, request)
        self.assertEqual(result['terms'], ['yo', 'People'])
        self.assertEqual(len(result['results']), 1)

    def test_community_search(self):
        context = testing.DummyModel()
        context.title = 'Citizens'
        from webob.multidict import MultiDict
        from opencore.models.interfaces import ICommunity
        from zope.interface import directlyProvides
        directlyProvides(context, ICommunity)
        request = testing.DummyRequest(params=MultiDict({'body':'yo'}))
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from repoze.lemonade.testing import registerContentFactory
        registerContentFactory(DummyContent, IDummyContent)
        testing.registerAdapter(DummySearch, (Interface),
                                ICatalogSearch)
        result = self._callFUT(context, request)
        self.assertEqual(result['community'], 'Citizens')
        self.assertEqual(result['terms'], ['yo'])
        self.assertEqual(len(result['results']), 1)

    def test_parse_error(self):
        from webob.multidict import MultiDict
        context = testing.DummyModel()
        request = testing.DummyRequest(params=MultiDict({'body':'the'}))
        from zope.interface import Interface
        from opencore.models.interfaces import ICatalogSearch
        from repoze.lemonade.testing import registerContentFactory
        registerContentFactory(DummyContent, IDummyContent)
        testing.registerAdapter(ParseErrorSearch, (Interface),
                                ICatalogSearch)
        result = self._callFUT(context, request)
        self.assertEqual(len(result['terms']), 0)
        self.assertEqual(len(result['results']), 0)
        self.assertEqual(result['error'], "Error: 'the' is nonsense")

class GetBatchTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, request):
        from opencore.views.search import get_batch
        return get_batch(context, request)

    def test_without_kind_with_terms(self):
        from webob.multidict import MultiDict
        from opencore.models.interfaces import ICatalogSearch
        testing.registerAdapter(DummySearch, (Interface),
                                ICatalogSearch)
        request = testing.DummyRequest(
            params=MultiDict({'body':'yo'}))
        context = testing.DummyModel()
        result = self._callFUT(context, request)
        self.assertEqual(result[0]['total'], 1)

    def test_without_kind_without_terms(self):
        from webob.multidict import MultiDict
        from opencore.models.interfaces import ICatalogSearch
        testing.registerAdapter(DummySearch, (Interface),
                                ICatalogSearch)
        request = testing.DummyRequest(params=MultiDict({}))
        context = testing.DummyModel()
        result = self._callFUT(context, request)
        self.assertEqual(len(result), 2)

    def test_with_kind_with_body(self):
        from opencore.models.interfaces import IGroupSearchFactory
        from repoze.lemonade.testing import registerListItem
        from webob.multidict import MultiDict
        content = DummyContent()
        def search_factory(*arg, **kw):
            return DummySearchFactory(content)
        registerListItem(IGroupSearchFactory, search_factory, 'dummy1',
                         title='Dummy1', sort_key=1)
        request = testing.DummyRequest(
            params=MultiDict({'body':'yo', 'kind':'dummy1'}))
        context = testing.DummyModel()
        result = self._callFUT(context, request)
        self.assertEqual(result[0]['total'], 1)

    def test_bad_kind_with_body(self):
        from webob.multidict import MultiDict
        from webob.exc import HTTPBadRequest
        request = testing.DummyRequest(
            params=MultiDict({'body':'yo', 'kind':'doesntexist'}))
        context = testing.DummyModel()
        self.assertRaises(HTTPBadRequest, self._callFUT, context, request)

    def test_with_kind_without_body(self):
        from opencore.models.interfaces import IGroupSearchFactory
        from repoze.lemonade.testing import registerListItem
        from webob.multidict import MultiDict
        def dummy_factory(context, request, term):
            def results():
                return 0, [], None
            return results
        registerListItem(IGroupSearchFactory, dummy_factory, 'dummy1',
                         title='Dummy1', sort_key=1)
        request = testing.DummyRequest(
            params=MultiDict({'kind':'dummy1'}))
        context = testing.DummyModel()
        result = self._callFUT(context, request)
        self.assertEqual(result,  (None, ()))

class MakeQueryTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, params):
        from webob.multidict import MultiDict
        from opencore.views.search import make_query
        context = testing.DummyModel()
        request = testing.DummyRequest(params=MultiDict(params))
        return make_query(context, request)

    def test_body_field(self):
        from repoze.lemonade.interfaces import IContent
        query, terms = self._callFUT({'body': 'yo'})
        self.assertEqual(query, {
            'texts': 'yo',
            'interfaces': [],
            'sort_index': 'texts',
            })
        self.assertEqual(terms, ['yo'])

    def test_creator_field(self):
        from zope.interface import Interface
        from zope.interface import implements
        from opencore.models.interfaces import ICatalogSearch
        from opencore.models.interfaces import IProfile

        searched_for = {}

        class Profile:
            implements(IProfile)
        profile = Profile()
        profile.__name__ = 'admin'

        class ProfileSearch:
            def __init__(self, context):
                pass
            def __call__(self, **kw):
                searched_for.update(kw)
                return 1, [1], lambda x: profile

        testing.registerAdapter(ProfileSearch, (Interface),
                                ICatalogSearch)
        query, terms = self._callFUT({'creator': 'Ad'})
        self.assertEquals(searched_for,
            {'texts': 'Ad', 'interfaces': [IProfile]})
        from repoze.lemonade.interfaces import IContent
        self.assertEqual(query, {
            'creator': {'query': ['admin'], 'operator': 'or'},
            'interfaces': [],
            })
        self.assertEqual(terms, ['Ad'])

    def test_types_field(self):
        from opencore.models.interfaces import IComment
        from repoze.lemonade.testing import registerContentFactory
        registerContentFactory(DummyContent, IComment)

        query, terms = self._callFUT(
            {'types': 'opencore_models_interfaces_IComment'})
        self.assertEqual(query, {'interfaces':
            {'query': [IComment], 'operator': 'or'}})
        self.assertEqual(terms, ['Comment'])

    def test_tags_field(self):
        from repoze.lemonade.interfaces import IContent
        query, terms = self._callFUT({'tags': 'a'})
        self.assertEqual(query, {
            'interfaces': [],
            'tags': {'query': ['a'], 'operator': 'or'},
            })
        self.assertEqual(terms, ['a'])

    def test_year_field(self):
        from repoze.lemonade.interfaces import IContent
        query, terms = self._callFUT({'year': '1990'})
        self.assertEqual(query,
            {'creation_date': (6311520, 6626483), 'interfaces': []})
        self.assertEqual(terms, [1990])


class AdvancedSearchViewTests(unittest.TestCase):

    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def test_advancedsearch_view(self):
        from opencore.models.interfaces import IComment
        from repoze.lemonade.testing import registerContentFactory
        registerContentFactory(DummyContent, IComment)

        context = testing.DummyModel()
        request = testing.DummyRequest()
        from opencore.views.api import get_template_api
        request.api = get_template_api(context, request)
        from opencore.views.search import advancedsearch_view
        result = advancedsearch_view(context, request)
        self.assertEqual(
            result['post_url'], 'http://example.com/searchresults.html')
        self.assertEqual(result['type_choices'], [
            ('Comment', 'opencore_models_interfaces_IComment'),
            ])
        self.assertFalse('2006' in result['year_choices'])
        self.assertTrue('2007' in result['year_choices'])


class DummySearch:
    def __init__(self, context):
        pass
    def __call__(self, **kw):
        return 1, [1], lambda x: dummycontent

class DummyEmptySearch:
    def __init__(self, context):
        pass
    def __call__(self, **kw):
        return 0, [], lambda x: None

class ParseErrorSearch:
    def __init__(self, context):
        pass
    def __call__(self, texts, **kw):
        from zope.index.text.parsetree import ParseError
        raise ParseError("'%s' is nonsense" % texts)

class DummySearchFactory:
    def __init__(self, content):
        self.content = content
    def get_batch(self):
        return {'entries':[self.content], 'total':1}

class IDummyContent(Interface):
    taggedValue('name', 'dummy')

class DummyContent(testing.DummyModel):
    implements(IDummyContent)

dummycontent = DummyContent()


import unittest

from repoze.bfg import testing

class FeedStorageTests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def test_test1(self):
        from opencore.feedstorage import Feed
        feed = Feed("example")
        import feedparser
        import os
        filename = os.path.join(
            os.path.dirname(__file__), 'feeds', 'test1.xml')
        parser = feedparser.parse(filename)
        parser['etag'] = 'xyz'
        parser['modified'] = 'today'

        feed.update(parser)

        self.assertEqual(feed.title, u'The Real Planet Planet')
        self.assertEqual(feed.subtitle, u'Life on Many Planets')
        self.assertEqual(feed.link, u'http://planet.example.com/')
        self.assertEqual(feed.etag, 'xyz')
        self.assertEqual(feed.feed_modified, 'today')
        self.assertEqual(feed.old_uri, None)
        self.assertEqual(feed.new_uri, None)

        self.assertEqual(len(feed.entries), 3)
        entry = feed.entries[0]

        self.assertEqual(entry.title, u'I Am Great')
        self.assertEqual(entry.summary, None)
        self.assertEqual(entry.link, None)
        self.assertEqual(entry.id, u'tag:12345')
        self.assertEqual(entry.content_html,
            '<div>\n        '
            'This is a well-researched essay about why I am great.\n      '
            '</div>')

        from datetime import datetime
        self.assertEqual(entry.published, datetime(2009, 4, 21, 10, 10, 0))
        self.assertEqual(entry.updated, datetime(2009, 4, 21, 10, 40, 2))

        entry = feed.entries[1]

        self.assertEqual(entry.title, u'Refutation of I Am Great')
        self.assertEqual(entry.summary, u"You're Wrong.")
        self.assertEqual(entry.link, None)
        self.assertEqual(entry.id, u'42')

        # Verify the content_html gets sanitized even with base64 encoding.
        self.assertEqual(entry.content_html, u'[]')

        self.assertEqual(entry.published, datetime(2009, 4, 21, 10, 10, 1))
        self.assertEqual(entry.updated, datetime(2009, 4, 21, 10, 40, 3))

        entry = feed.entries[2]
        self.assertEqual(entry.title, None)
        self.assertEqual(entry.summary, None)
        self.assertEqual(entry.link, None)
        self.assertEqual(entry.id, None)
        self.assertEqual(entry.content_html, None)
        self.assertEqual(entry.published, None)
        self.assertEqual(entry.updated, None)



    def test_entry_equality(self):
        from opencore.feedstorage import Feed
        import feedparser
        import os
        filename = os.path.join(
            os.path.dirname(__file__), 'feeds', 'test1.xml')

        parser1 = feedparser.parse(filename)
        feed1 = Feed("example")
        feed1.update(parser1)

        parser2 = feedparser.parse(filename)
        feed2 = Feed("example")
        feed2.update(parser2)

        self.assertEqual(feed1.entries, feed2.entries)
        self.assertFalse(feed1.entries[0] != feed2.entries[0])
        self.assertFalse(feed1.entries[1] != feed2.entries[1])

    def test_empty_upstream_feed(self):
        from opencore.feedstorage import Feed
        import feedparser
        import os
        filename = os.path.join(
            os.path.dirname(__file__), 'feeds', 'test1.xml')

        parser = feedparser.parse(filename)
        feed = Feed("example")
        feed.update(parser)
        self.assertEqual(len(feed.entries), 3)

        filename = os.path.join(
            os.path.dirname(__file__), 'feeds', 'test0.xml')
        parser = feedparser.parse(filename)
        feed.update(parser)
        self.assertEqual(len(feed.entries), 3)

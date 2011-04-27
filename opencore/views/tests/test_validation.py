from opencore.views.validation import safe_html
from testfixtures import compare
from unittest import TestCase

class TestSafeHTML(TestCase):

    def test_tags(self):
        compare(
            '<strong>hello</strong><em>out</em><p>there.</p>',
            safe_html('<strong>hello</strong><em>out</em>there.')
            )

    def test_unmatched(self):
        compare(
            '<strong>hello<em>out there.</em></strong>',
            safe_html('<strong>hello<em>out there.')
            )

    def test_evil(self):
        compare(
            '<strong><a href="">out</a></strong>',
            safe_html(
                '<strong hello</strong><a href="javascript:alert("evil")">out</a>')
            )

    def test_page(self):
        compare(
            '<p>hello out there.</p>',
            safe_html('<html><body>hello out there.</body></html>')
            )

    def test_plain_text(self):
        compare(
            '<p>hello out there.</p>',
            safe_html('hello out there.')
            )

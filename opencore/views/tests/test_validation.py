from opencore.views.validation import safe_html
from testfixtures import compare
from unittest import TestCase

class TestSafeHTML(TestCase):

    def test_tags(self):
        compare(
            'hello\nout\nthere.',
            safe_html('<b>hello</b><i>out</i>there.')
            )

    def test_unmatched(self):
        compare(
            'hello\nout there.',
            safe_html('<b>hello<i>out there.')
            )

    def test_evil(self):
        compare(
            'out',
            safe_html(
                '<b hello</b><a href="javascript:alert("evil")">out</a>')
            )

    def test_page(self):
        compare(
            'hello out there.',
            safe_html('<html><body>hello out there.</body></html>')
            )

    def test_plain_text(self):
        compare(
            'hello out there.',
            safe_html('hello out there.')
            )

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

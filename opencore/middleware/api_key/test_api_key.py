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

import unittest
from repoze.bfg import testing
from opencore.middleware.api_key import make_plugin
class TestAPIKey(unittest.TestCase):

    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _create_plugin(self, keys='one, two, three'):
        return make_plugin('key', keys=keys, user_name='api')

    def test_good_key(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : "key=one&something=2"})
        self.assertEqual(result['repoze.who.userid'], 'api')

    def test_good_key_in_set_of_one(self):
        plugin = self._create_plugin('a')
        result = plugin.identify({'QUERY_STRING' : "key=a&something=2"})
        self.assertEqual(result['repoze.who.userid'], 'api')

    def test_bad_key(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : "key=xxx&something=2"})
        self.assertTrue(result is None)

    def test_missing_key(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : "something=2"})
        self.assertTrue(result is None)

    def test_no_query_string(self):
        plugin = self._create_plugin()
        result = plugin.identify({'QUERY_STRING' : None})
        self.assertTrue(result is None)

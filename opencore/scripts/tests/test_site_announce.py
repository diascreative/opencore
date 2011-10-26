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

from opencore import testing


class Test_clear_site_announce(unittest.TestCase):

    def _callFUT(self, root):
        from opencore.scripts.site_announce import clear_site_announce
        return clear_site_announce(root)

    def test_it(self):
        root = testing.DummyModel(site_announcement='TESTING')
        previous, now = self._callFUT(root)
        self.assertEqual(previous, 'TESTING')
        self.assertEqual(now, '')
        self.assertEqual(root.site_announcement, '')


class Test_site_announce(unittest.TestCase):

    def _callFUT(self, root, *args):
        from opencore.scripts.site_announce import set_site_announce
        return set_site_announce(root, *args)

    def test_no_args_no_current(self):
        root = testing.DummyModel()
        previous, now = self._callFUT(root)
        self.assertEqual(previous, '')
        self.assertEqual(now, '')
        self.failIf('site_announcement' in root.__dict__)

    def test_no_args_returns_current(self):
        root = testing.DummyModel(site_announcement='TESTING')
        previous, now = self._callFUT(root)
        self.assertEqual(previous, 'TESTING')
        self.assertEqual(now, 'TESTING')
        self.assertEqual(root.site_announcement, 'TESTING')

    def test_w_new_value(self):
        root = testing.DummyModel(site_announcement='TESTING')
        previous, now = self._callFUT(root, 'UPDATED')
        self.assertEqual(previous, 'TESTING')
        self.assertEqual(now, 'UPDATED')
        self.assertEqual(root.site_announcement, 'UPDATED')

    def test_w_new_value_multiple(self):
        root = testing.DummyModel(site_announcement='TESTING')
        previous, now = self._callFUT(root, 'MULTIPLE', 'ARGUMENTS')
        self.assertEqual(previous, 'TESTING')
        self.assertEqual(now, 'MULTIPLE ARGUMENTS')
        self.assertEqual(root.site_announcement, 'MULTIPLE ARGUMENTS')

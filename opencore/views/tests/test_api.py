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
import unittest, uuid

# Repoze
from repoze.bfg import testing

# opencore
from opencore.views.api import TemplateAPI

class TestAPI(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

        
    def test_user_is_staff_is_iterable(self):
        environ={'repoze.who.identity':{uuid.uuid4().hex:uuid.uuid4().hex}}
        request = testing.DummyRequest(environ=environ)
        
        api = TemplateAPI(None, request, None)
        
        # Should return False which is fine because the whole point is to
        # actually make sure that whatever API's self._identity returns
        # is a dictionary.
        self.assertEquals(api.user_is_staff, False)
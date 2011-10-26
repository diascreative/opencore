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

from cStringIO import StringIO
from mock import Mock
from opencore.models.interfaces import ICommunityFile
from opencore.views.utils import (
    handle_photo_upload,
    make_name,
    )
from repoze.bfg import testing
from repoze.lemonade.testing import registerContentFactory
from unittest import TestCase
from testfixtures import (
    compare,
    Replacer,
    ShouldRaise
    )

from .test_people import (
    DummyImageFile,
    DummyProfile,
    )

class TestMakeName(TestCase):

    def setUp(self):
        self.context = testing.DummyModel()
        
    def test_simple(self):
        self.assertEqual(
            make_name(self.context,'something'),
            'something'
            )

    def test_complex(self):
        self.assertEqual(
            make_name(self.context,'$%^some thing'),
            'some-thing'
            )

    def test_exists_one(self):
        self.context['name']=testing.DummyModel()
        self.assertEqual(
            make_name(self.context,'name'),
            'name-2'
            )

    def test_exists_two(self):
        self.context['name']=testing.DummyModel()
        self.context['name-2']=testing.DummyModel()
        self.assertEqual(
            make_name(self.context,'name'),
            'name-3'
            )
    
    def test_empty(self):
        with ShouldRaise(ValueError('The name must not be empty')):
            make_name(self.context,'')

    def test_empty_cos_of_dodgy_characters(self):
        with ShouldRaise(ValueError('The name must not be empty')):
            make_name(self.context,'$%')

class Test_handle_photo_upload(TestCase):

    def setUp(self):
        testing.cleanUp()
        registerContentFactory(DummyImageFile,ICommunityFile)
        self.cstruct = {
            'fp': StringIO('some image data'),
            'mimetype': 'image/jpeg',
            'filename': u'test.jpg',
            }
        self.context = DummyProfile()
        self.authenticated_userid = Mock()
        self.authenticated_userid.return_value = 'auser'
        self.r = Replacer()
        self.r.replace('opencore.views.utils.authenticated_userid',
                       self.authenticated_userid)

    def tearDown(self):
        self.r.restore()
        testing.cleanUp()
        
    def test_no_cstruct(self):
        handle_photo_upload(self.context,None,None)
        self.assertFalse(self.context.get('photo'))

    def test_no_existing_photo(self):
        handle_photo_upload(self.context,None,self.cstruct)
        content = self.context['photo']
        compare(content.title,'Photo of firstname lastname')
        compare(content.mimetype,'image/jpeg')
        compare(content.filename,'test.jpg')
        compare(content.creator,'auser')

    def test_existing_photo(self):
        self.context['photo']=testing.DummyModel()
        handle_photo_upload(self.context,None,self.cstruct)
        content = self.context['photo']
        compare(content.title,'Photo of firstname lastname')
        compare(content.mimetype,'image/jpeg')
        compare(content.filename,'test.jpg')
        compare(content.creator,'auser')


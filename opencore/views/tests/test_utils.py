from opencore.views.utils import make_name
from unittest import TestCase
from testfixtures import ShouldRaise
from repoze.bfg.testing import DummyModel

class TestMakeName(TestCase):

    def setUp(self):
        self.context = DummyModel()
        
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
        self.context['name']=DummyModel()
        self.assertEqual(
            make_name(self.context,'name'),
            'name-2'
            )

    def test_exists_two(self):
        self.context['name']=DummyModel()
        self.context['name-2']=DummyModel()
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

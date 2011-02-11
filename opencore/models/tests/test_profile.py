import unittest
from repoze.bfg import testing

class ProfileTests(unittest.TestCase):

    def setUp(self):
        from zope.testing.cleanup import cleanUp
        cleanUp()

    def tearDown(self):
        from zope.testing.cleanup import cleanUp
        cleanUp()

    def _getTargetClass(self):
        from opencore.models.profile import Profile
        return Profile

    def _makeOne(self, **kw):
        return self._getTargetClass()(**kw)

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from opencore.models.interfaces import IProfile
        verifyClass(IProfile, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IProfile
        verifyObject(IProfile, self._makeOne())

    def test_ctor(self):
        inst = self._makeOne(firstname='fred')
        self.assertEqual(inst.firstname, 'fred')

    def test_creator_is___name__(self):
        from repoze.bfg.testing import DummyModel
        profiles = DummyModel()
        inst = profiles['flinty'] = self._makeOne(firstname='fred',
                                                  lastname='flintstone ')

        self.assertEqual(inst.creator, 'flinty')

    def test_title(self):
        inst = self._makeOne(firstname='fred', lastname='flintstone ')
        self.assertEqual(inst.title, 'fred flintstone')

    def test_title_inactive(self):
        inst = self._makeOne(firstname='fred', lastname='flintstone ')
        inst.security_state = 'inactive'
        self.assertEqual(inst.title, 'fred flintstone (Inactive)')

    def test_folderish(self):
        from repoze.folder import Folder
        from repoze.folder.interfaces import IFolder
        cls = self._getTargetClass()
        self.failUnless(IFolder.implementedBy(cls))
        o = self._makeOne()
        self.failUnless(IFolder.providedBy(o))
        self.failUnless(isinstance(o, Folder))
        self.failUnless(hasattr(o, "data"))

    def test_alert_prefs(self):
        from opencore.models.interfaces import IProfile
        inst = self._makeOne()
        self.assertEqual(IProfile.ALERT_IMMEDIATELY,
                         inst.get_alerts_preference("foo"))
        inst.set_alerts_preference("foo", IProfile.ALERT_DIGEST)
        self.assertEqual(IProfile.ALERT_DIGEST,
                         inst.get_alerts_preference("foo"))
        inst.set_alerts_preference("foo", IProfile.ALERT_NEVER)
        self.assertEqual(IProfile.ALERT_NEVER,
                         inst.get_alerts_preference("foo"))

        self.assertRaises(ValueError, inst.set_alerts_preference, "foo", 13)

    def test_verify_alert_prefs_persistent(self):
        from persistent.mapping import PersistentMapping
        inst = self._makeOne()
        self.failUnless(isinstance(inst._alert_prefs, PersistentMapping))

    def test_pending_alerts(self):
        inst = self._makeOne()
        self.assertEqual(0, len(inst._pending_alerts))
        inst._pending_alerts.append( "FOO" )
        self.assertEqual(1, len(inst._pending_alerts))
        self.assertEqual("FOO", inst._pending_alerts.pop(0))
        self.assertEqual(0, len(inst._pending_alerts))

    def test_pending_alerts_persistent(self):
        from persistent.list import PersistentList
        inst = self._makeOne()
        self.failUnless(isinstance(inst._pending_alerts, PersistentList))

    def test_empty_country(self):
        inst = self._makeOne()
        self.assertEqual(inst.country, 'XX')

    def test_invalid_country(self):
        inst = self._makeOne(country='XY')
        self.assertEqual(inst.country, 'XX')

    def test_valid_country(self):
        inst = self._makeOne(country='HT')
        self.assertEqual(inst.country, 'HT')

    def test_website_websites_new_instance(self):
        inst = self._makeOne()
        self.assertEqual(list(inst.websites), [])

    def test_websites_as_empty_list(self):
        inst = self._makeOne(websites=[])
        self.assertEqual(inst.websites, [])

class ProfilesFolderTests(unittest.TestCase):

    def setUp(self):
        from zope.testing.cleanup import cleanUp
        cleanUp()

    def tearDown(self):
        from zope.testing.cleanup import cleanUp
        cleanUp()

    def _getTargetClass(self):
        from opencore.models.profile import ProfilesFolder
        return ProfilesFolder

    def _makeOne(self, **kw):
        return self._getTargetClass()(**kw)

    def test_verifyImplements(self):
        from zope.interface.verify import verifyClass
        from opencore.models.interfaces import IProfiles
        verifyClass(IProfiles, self._getTargetClass())

    def test_verifyProvides(self):
        from zope.interface.verify import verifyObject
        from opencore.models.interfaces import IProfiles
        verifyObject(IProfiles, self._makeOne())

    def test___init___defaults(self):
        pf = self._makeOne()
        self.assertEqual(len(pf.email_to_name), 0)
        self.assertEqual(pf.email_to_name.get('nonesuch'), None)

    def test_getProfileByEmail_miss(self):
        pf = self._makeOne()
        self.assertEqual(pf.getProfileByEmail('nonesuch@example.com'), None)

    def test_getProfileByEmail_hit(self):
        from repoze.bfg.testing import DummyModel
        pf = self._makeOne()
        profile = pf['extant'] = DummyModel()
        pf.email_to_name['extant@example.com'] = 'extant'
        self.failUnless(pf.getProfileByEmail('extant@example.com') is profile)

    def test_getProfileByEmail_mixedcase(self):
        from repoze.bfg.testing import DummyModel
        pf = self._makeOne()
        profile = pf['extant'] = DummyModel()
        pf.email_to_name['eXtant@example.com'] = 'extant'
        self.failUnless(pf.getProfileByEmail('Extant@example.com') is profile)


class Test_profile_textindexdata(unittest.TestCase):

    def _callFUT(self, profile):
        from opencore.models.profile import profile_textindexdata
        return profile_textindexdata(profile)

    def test_no_attrs(self):
        callable = self._callFUT(object())
        self.assertEqual(callable(), '')

    def test_w_all_attrs(self):
        from repoze.bfg.testing import DummyModel
        ATTR_NAMES = [
            '__name__',
            'firstname',
            'lastname',
            'email',
            'phone',
            'extension',
            'department',
            'position',
            'organization',
            'location',
            'country',
            'website',
            'languages',
            'office',
            'room_no',
            'biography',
        ]
        ATTR_VALUES = [x.upper() for x in ATTR_NAMES]
        mapping = dict(zip(ATTR_NAMES, ATTR_VALUES))
        profile = DummyModel(**mapping)
        callable = self._callFUT(profile)
        self.assertEqual(callable(), '\n'.join(ATTR_VALUES))

    def test_w_extra_attrs(self):
        from repoze.bfg.testing import DummyModel
        profile = DummyModel(firstname='Phred',
                             lastname='Phlyntstone',
                             town='Bedrock',
                            )
        callable = self._callFUT(profile)
        self.assertEqual(callable(), 'Phred\nPhlyntstone')

    def test_w_UTF8_attrs(self):
        from repoze.bfg.testing import DummyModel
        FIRSTNAME = u'Phr\xE9d'
        profile = DummyModel(firstname=FIRSTNAME.encode('UTF8'))
        callable = self._callFUT(profile)
        self.assertEqual(callable(), FIRSTNAME)

    def test_w_latin1_attrs(self):
        from repoze.bfg.testing import DummyModel
        FIRSTNAME = u'Phr\xE9d'
        profile = DummyModel(firstname=FIRSTNAME.encode('latin1'))
        callable = self._callFUT(profile)
        self.assertEqual(callable(), FIRSTNAME)
        
class TestProfileCategoryGetter(unittest.TestCase):

    def _makeFolder(self, mapping):
        class DummyFolder(dict):
            pass
        return DummyFolder(mapping)
    
   

    def test_non_profile(self):
        from opencore.models.profile import ProfileCategoryGetter
        getter = ProfileCategoryGetter('office')
        obj = testing.DummyModel()
        obj.categories = {'office': ['slc']}
        self.assertEqual(getter(obj, 0), 0)

    def test_success(self):
        from opencore.models.profile import ProfileCategoryGetter
        getter = ProfileCategoryGetter('office')
        obj = _makeProfile()
        obj.categories = {'office': ['slc']}
        self.assertEqual(getter(obj, 0), ['slc'])

    def test_empty_category(self):
        from opencore.models.profile import ProfileCategoryGetter
        getter = ProfileCategoryGetter('office')
        obj = _makeProfile()
        obj.categories = {'office': []}
        self.assertEqual(getter(obj, 0), 0)

    def test_no_categories(self):
        from opencore.models.profile import ProfileCategoryGetter
        getter = ProfileCategoryGetter('office')
        obj = _makeProfile()
        obj.categories = {}
        self.assertEqual(getter(obj, 0), 0)
        
def _makeProfile(**kw):
    from zope.interface import implements
    from opencore.models.interfaces import IProfile
    
    class DummyProfile(testing.DummyModel):
        implements(IProfile)
    
    return DummyProfile(**kw)

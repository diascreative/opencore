import os
import unittest
from repoze.bfg import testing


class TestMessengerFactory(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, os=os):
        from opencore.utilities.messenger import messenger_factory
        return messenger_factory(os=os)

    def test_no_settings(self):
        from opencore.utilities.messenger import FakeMessenger
        delivery = self._callFUT()
        self.assertEqual(delivery.__class__, FakeMessenger)

    def test_with_settings_and_suppress_messenger(self):
        from repoze.bfg.interfaces import ISettings
        from opencore.utilities.messenger import FakeMessenger
        settings = DummySettings()
        testing.registerUtility(settings, ISettings)
        os = FakeOS(SUPPRESS_MESSENGER='1')
        delivery = self._callFUT(os)
        self.assertEqual(delivery.__class__, FakeMessenger)
        
    def test_with_settings_for_real_messenger(self):
        from repoze.bfg.interfaces import ISettings
        from opencore.utilities.messenger import Messenger
        settings = DummySettings()
        testing.registerUtility(settings, ISettings)
        os = FakeOS()
        delivery = self._callFUT(os)
        self.assertEqual(delivery.__class__, Messenger) 
     
        
    def test_send_to_suppressed_messenger(self):
        from repoze.bfg.interfaces import ISettings
        settings = DummySettings()
        testing.registerUtility(settings, ISettings)
        os = FakeOS(SUPPRESS_MESSENGER='1')
        delivery = self._callFUT(os)
        joe = DummyProfile(name='joe')
        delivery.quiet = False
        delivery.send("a", joe, "frankly I don't give a damn!") 


class TestMessenger(unittest.TestCase):
   
    def _set_alerts_off(self):
        from repoze.bfg.testing import registerUtility
        from repoze.bfg.interfaces import ISettings
        settings = DummySettings(alert_notifications_on=False)
        registerUtility(settings, ISettings)

    def setUp(self):
        from repoze.bfg.testing import registerUtility
        from opencore.models.interfaces import ISite
        testing.setUp()
        self._set_alerts_off()
        from opencore.utilities import mbox
        self.tx = mbox.transaction = DummyTransaction()
        self.root = testing.DummyModel()
        self.root['mailbox'] = testing.DummyModel()
        registerUtility(self.root, ISite)

    def tearDown(self):
        testing.tearDown()

    def test_send(self):
        from opencore.utilities.messenger import Messenger
        messenger = Messenger()
        joe = DummyProfile(name='joe')
        # messenger.send uses find_site(profile) to look up root so
        # place joe in a 'locatable' path
        joe.__parent__ = self.root
             
        joes_queue = DummyQueue() 
        self.root['mailbox']['joe'] = joes_queue
         
        messenger.send("a", joe, "frankly I don't give a damn!")
        self.assertEqual(1, len(joes_queue))
        self.assertEqual('a', joes_queue[0]['From'])
        self.assertEqual("frankly I don't give a damn!", joes_queue[0].get_payload())

    def test_sending_bad_msg(self):
        from opencore.utilities.messenger import Messenger
        messenger = Messenger()
        joe = DummyProfile(name='joe')
        joe.__parent__ = self.root
             
        joes_queue = DummyQueue() 
        self.root['mailbox']['joe'] = joes_queue
        self.assertRaises(TypeError, lambda : messenger.send("a", joe, 99))


class DummyMessenger(object):
    def __init__(self):
        self.calls = []

    def send(self, fromaddr, toaddrs, message):
        self.calls.append(dict(
            fromaddr=fromaddr,
            toaddrs=toaddrs,
            message=message,
        ))

class DummySettings:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

class FakeOS:
    def __init__(self, **environ):
        self.environ = environ

from zope.interface import implements        
from opencore.models.interfaces import IProfile        
class DummyProfile(testing.DummyModel):
    implements(IProfile)

    title = 'title'
    firstname = 'firstname'
    lastname = 'lastname'
    position = 'position'
    organization = 'organization'
    phone = 'phone'
    extension = 'extension'
    department = 'department1'
    location = 'location'
    alert_attachments = 'link'

    def __init__(self, *args, **kw):
        testing.DummyModel.__init__(self)
        for item in kw.items():
            setattr(self, item[0], item[1])
        self._alert_prefs = {}
        self._pending_alerts = []
        self.__name__ = kw['name']

    @property
    def email(self):
        return "%s@x.org" % self.__name__

    def get_photo(self):
        return None

    def get_alerts_preference(self, community_name):
        return self._alert_prefs.get(community_name,
                                     IProfile.ALERT_IMMEDIATELY)

    def set_alerts_preference(self, community_name, preference):
        if preference not in (
            IProfile.ALERT_IMMEDIATELY,
            IProfile.ALERT_DIGEST,
            IProfile.ALERT_NEVER):
            raise ValueError("Invalid preference.")

        self._alert_prefs[community_name] = preference
    
class DummyQueue(list):
   
    duplicate = False

    def add(self, message):
        self.append(message)
    
    def __iter__(self):
        return iter(self)
    
    def pop_next(self):
        return self.pop(0)

    def is_duplicate(self, message):
        return self.duplicate


class DummyTransaction(object):
    committed = False
    aborted = False

    def commit(self):
        self.committed = True

    def abort(self):
        self.aborted = True    

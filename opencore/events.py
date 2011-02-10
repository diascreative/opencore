from zope.interface import implements
from opencore.interfaces import IObjectModifiedEvent
from opencore.interfaces import IObjectWillBeModifiedEvent

class ObjectModifiedEvent(object):
    implements(IObjectModifiedEvent)
    def __init__(self, object):
        self.object = object

class ObjectWillBeModifiedEvent(object):
    implements(IObjectWillBeModifiedEvent)
    def __init__(self, object):
        self.object = object
        

from opencore.interfaces import IObjectModifiedEvent
from opencore.interfaces import IObjectWillBeModifiedEvent

from zope.interface import implements

class ObjectModifiedEvent(object):
    implements(IObjectModifiedEvent)
    def __init__(self, object):
        self.object = object

class ObjectWillBeModifiedEvent(object):
    implements(IObjectWillBeModifiedEvent)
    def __init__(self, object):
        self.object = object


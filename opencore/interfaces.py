from zope.interface import Attribute
from zope.component.interfaces import IObjectEvent

class IObjectWillBeModifiedEvent(IObjectEvent):
    """ An event type sent before an object is modified  """
    object = Attribute('The object that will be modified')

class IObjectModifiedEvent(IObjectEvent):
    """ An event type sent after an object is modified """
    object = Attribute('The object which was modified')


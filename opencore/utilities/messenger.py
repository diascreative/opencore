from __future__ import with_statement

import os

from zope.interface import implements
from zope.component import queryUtility
from repoze.bfg.interfaces import ISettings
from repoze.bfg.settings import asbool
from opencore.utils import find_site
from opencore.utilities.interfaces import IMessenger
from opencore.utilities.mbox import Mailbox
from opencore.utilities.message import MboxMessage
import logging

log = logging.getLogger(__name__)

def messenger_factory(os=os): # accepts 'os' for unit test purposes
    """Factory method for creating an instance of IMessenger
    for use by this application.
    """
    settings = queryUtility(ISettings)

    # If settings utility not present, we are probably testing and should
    # suppress sending mail.  Can also be set explicitly in environment
    # variable
    suppress_messenger = asbool(os.environ.get('SUPPRESS_MESSENGER', ''))

    if settings is None or suppress_messenger:
        return FakeMessenger()
 
    return Messenger()


class Messenger(object):
    implements(IMessenger)

    def send(self, mfrom, profile, msg):
        root = find_site(profile)
        queue = Mailbox.open_queue(root, profile.__name__)
        if not isinstance(msg, MboxMessage):
            try:
                msg = MboxMessage(msg)
            except Exception, e:
                log.warning('Unable to convert to MboxMessage from  received '
                            'type (%s)' % msg.__class__.__name__) 
                raise e   
        msg['from'] = mfrom
        queue.add(msg)   

class FakeMessenger:
    implements(IMessenger)

    def __init__(self, quiet=True):
        self.quiet = quiet

    def send(self, mfrom, profile, msg):
        if not self.quiet:
            log.info('Sent Message=%s, From=%s, To=%s' % (msg,
              mfrom, profile.__name__))
          


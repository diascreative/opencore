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
from datetime import datetime

# Zope
import transaction

# Repoze
from repoze.bfg import testing
from repoze.folder import Folder

# testfixtures
from testfixtures import LogCapture

# opencore
from opencore.scripting import get_default_config
from opencore.scripting import open_root
from opencore.utilities.mbox import MailboxTool
from opencore.utilities.mbox import MboxMessage
from opencore.utilities.mbox import NoSuchThreadException
from opencore.utilities.mbox import Queue

def get_data():

    site, _ = open_root(get_default_config())
    now = str(datetime.utcnow())

    from_ = 'admin'
    to = ['joe', 'sarah']

    subject = uuid.uuid4().hex
    payload = uuid.uuid4().hex
    flags = ['read']

    thread_id = 'openhcd.' + uuid.uuid4().hex
    msg_id = 'openhcd.' +  now + '.' + uuid.uuid4().hex

    msg = MboxMessage(payload)
    msg['Message-Id'] = msg_id
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = ', '.join(to)
    msg['Date'] = now
    msg['X-oc-thread-id'] = thread_id
    msg['X-people-list'] = 'admin'

    return site, from_, to, msg, thread_id, msg_id, flags, subject, payload, now

class TestMailbox(unittest.TestCase):

    def setUp(self):
        self.mbt = MailboxTool()
        self.log = LogCapture()

    def zztest_send_get_message(self):
        site, from_, to, msg, thread_id, msg_id, _, subject, payload, now = get_data()
        self.mbt.send_message(site, from_, to, msg)

        raw_msg, msg = self.mbt.get_message(site, from_, 'sent', thread_id, msg_id)

        self.assertEquals(raw_msg.message_id, msg_id)
        self.assertEquals(raw_msg.flags, [])

        self.assertEquals(msg['Message-Id'], msg_id)
        self.assertEquals(msg['Subject'], subject)
        self.assertEquals(msg['From'], from_)
        self.assertEquals(msg['To'], ', '.join(to))
        self.assertEquals(msg['Date'],  now)
        self.assertEquals(msg['X-oc-thread-id'], thread_id)
        
        transaction.commit()

    def zztest_delete_message(self):
        site, from_, to, msg, thread_id, msg_id, _, subject, payload, now = get_data()
        self.mbt.send_message(site, from_, to, msg)
        self.mbt.delete_message(site, from_, 'sent', thread_id, msg_id)

        try:
            self.mbt.get_message(site, from_, 'sent', thread_id, msg_id)
        except NoSuchThreadException:
            pass
        else:
            raise
        
        transaction.commit()

    def zztest_set_message_flags(self):
        site, from_, to, msg, thread_id, msg_id, flags, subject, payload, now = get_data()
        self.mbt.send_message(site, from_, to, msg)
        self.mbt.set_message_flags(site, from_, 'sent', thread_id, msg_id, flags)

        raw_msg, msg = self.mbt.get_message(site, from_, 'sent', thread_id, msg_id)
        self.assertEquals(raw_msg.flags, flags)

        raw_msg, msg = self.mbt.get_message(site, from_, 'sent', thread_id, msg_id)
        
        transaction.commit()

    def zztest_get_queues(self):
        site, from_, to, msg, thread_id, msg_id, _, subject, payload, now = get_data()
        self.mbt.send_message(site, from_, to, msg)
        queues = self.mbt.get_queues(site, from_, 'sent')

        for queue in queues:
            self.assertTrue(isinstance(queue, Queue))
            
        transaction.commit()


# stdlib
import unittest, uuid
from datetime import datetime

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


class TestMailbox(unittest.TestCase):

    def setUp(self):
        self.mbt = MailboxTool()
        self.log = LogCapture()

    def get_data(self):

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

        return site, from_, to, msg, thread_id, msg_id, flags, subject, payload, now

    def test_send_get_message(self):
        site, from_, to, msg, thread_id, msg_id, _, subject, payload, now = self.get_data()
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

    def test_delete_message(self):
        site, from_, to, msg, thread_id, msg_id, _, subject, payload, now = self.get_data()
        self.mbt.send_message(site, from_, to, msg)
        self.mbt.delete_message(site, from_, 'sent', thread_id, msg_id)

        try:
            self.mbt.get_message(site, from_, 'sent', thread_id, msg_id)
        except NoSuchThreadException:
            pass
        else:
            raise

    def test_set_message_flags(self):
        site, from_, to, msg, thread_id, msg_id, flags, subject, payload, now = self.get_data()
        self.mbt.send_message(site, from_, to, msg)
        self.mbt.set_message_flags(site, from_, 'sent', thread_id, msg_id, flags)

        raw_msg, msg = self.mbt.get_message(site, from_, 'sent', thread_id, msg_id)
        self.assertEquals(raw_msg.flags, flags)

        raw_msg, msg = self.mbt.get_message(site, from_, 'sent', thread_id, msg_id)

    def test_get_queues(self):
        site, from_, to, msg, thread_id, msg_id, _, subject, payload, now = self.get_data()
        self.mbt.send_message(site, from_, to, msg)
        queues = self.mbt.get_queues(site, from_, 'sent')

        for queue in queues:
            self.assertTrue(isinstance(queue, Queue))
            
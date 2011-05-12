import unittest

#import openideo.tests.utils as openideotesting


class TestMailbox(unittest.TestCase):
    def setUp(self):
        from opencore.utilities import mbox
        self.tx = mbox.transaction = DummyTransaction()
        self.root = {}

    def tearDown(self):
        pass

    def _make_one(self, users, queues=None, db_path='/mailbox'):
        from opencore.utilities.mbox import Mailbox
        import os

        DummyDB(self.root, queues, db_path)
        mb = Mailbox(root=self.root, users=users, path=db_path)
        mb.Queue = DummyQueue
        return mb


    def zztest_open_queue_with_no_mailbox(self):
        from opencore.utilities.mbox import Mailbox
        self.assertRaises(KeyError, Mailbox.open_queue, self.root, user='bogus', path='mailbox')

    def zztest_open_queue_with_unknown_user(self):
         from opencore.utilities.mbox import Mailbox
         mb = self._make_one(users=['foo'])
         self.assertRaises(KeyError, Mailbox.open_queue, self.root, user='the-unknown', path='mailbox')

    def zztest_open_queue_with_no_mailbox(self):
        from opencore.utilities.mbox import Mailbox
        self.assertRaises(KeyError, Mailbox.open_queue, self.root, user='bogus', path='mailbox')

    def zztest_open_queue_with_unknown_mailbox_path(self):
        from opencore.utilities.mbox import Mailbox
        self.assertRaises(KeyError, Mailbox.open_queue, self.root, user='bogus', path='/bogus/path')

    def zztest_open_queue(self):
         from opencore.utilities.mbox import Mailbox
         mb = self._make_one(users=['fred'])
         qr = Mailbox.open_queue(self.root, user='fred', path='mailbox')
         self.assertEqual(qr, self.root['mailbox']['fred'])


    def zztest_ctor_queues(self):
        users = ['john', 'mary']
        mb = self._make_one(users)

        queues = mb.configured_queues
        self.assertEqual(len(queues), 2)
        queue = queues.pop(0)
        self.assertEqual(queue['name'], 'john')
        queue = queues.pop(0)
        self.assertEqual(queue['name'], 'mary')


    def zztest_ctor_bad_queue_parameter(self):
        self.assertRaises(TypeError, self._make_one, None)


    def zztest_reconcile_queues_from_scratch(self):
        users = ['john', 'mary']
        mb = self._make_one(users)
        self.failUnless('mailbox' in self.root)
        queues = self.root['mailbox']
        self.failUnless('john' in queues)
        self.failUnless('mary' in queues)
        self.failUnless(self.tx.committed)

    def zztest_reconcile_queues_rm_old(self):
        log = DummyLogger()
        users = ['john', 'mary']
        mb = self._make_one(users)
        self.failUnless('mailbox' in self.root)
        queues = self.root['mailbox']

        self.failUnless('john' in queues)
        self.failUnless('mary' in queues)
        self.failUnless(self.tx.committed)

        new_queues = [{'name': 'foo'}]
        mb.configured_queues= new_queues
        mb.reconcile_queues(log)
        self.failIf('john' in queues)
        self.failIf('mary' in queues)
        self.failUnless('foo' in queues)
        self.failUnless(self.tx.committed)
        self.assertEqual(len(log.infos), 3)

    def zztest_reconcile_queues_error(self):
        mb = self._make_one([])
        self.failUnless('mailbox' in self.root)
        queues = self.root['mailbox']

        new_queues = [{'no-name-key': 'foo'}]
        mb.configured_queues= new_queues
        self.assertRaises(KeyError, mb.reconcile_queues)
        self.failUnless(self.tx.aborted)

    def zztest_get_mailbox_error(self):
        from repoze.bfg.testing import DummyModel
        mb = self._make_one(users=[])
        root = RaiseRootException()
        db = DummyDB(root, queues=DummyModel(), db_path='/mailbox')
        self.assertRaises(KeyError, mb._get_mailbox, db.root(), '/mailbox')

    def zztest_get_mailbox_error2(self):
        from repoze.bfg.testing import DummyModel
        mb = self._make_one(users=[])
        root = RaiseRootException()
        db = DummyDB(root, queues=DummyModel(), db_path='/mailbox')
        self.assertRaises(KeyError, mb._get_mailbox, db.root(), '/bogus/path/to/mailbox')

class TestQueue(unittest.TestCase):

    def setUp(self):
        from opencore.utilities import mbox
        self.tx = mbox.transaction = DummyTransaction()

    def _make_one(self):
        from opencore.utilities.mbox import Queue
        return Queue()

    def zztest_add_and_iterate_messages(self):
        queue = self._make_one()
        queue.add(DummyMessage('one'))
        self.assertEqual(len(queue), 1)
        self.failUnless(queue)
        queue.add(DummyMessage('two'))
        self.assertEqual(len(queue), 2)

        iter_msgs = []
        for msg in queue:
            iter_msgs.append(msg)

        self.assertEqual(len(iter_msgs), 2)
        self.assertEqual(len(queue), 2)

        index_msgs = []
        for index in range(len(queue)):
            index_msgs.append(queue[index])

        self.assertEqual(len(index_msgs), 2)
        self.assertEqual(len(queue), 2)

        self.assertEqual(iter_msgs[0], index_msgs[0])
        self.assertEqual(iter_msgs[1], index_msgs[1])


    def zztest_add_and_retrieve_messages(self):
        queue = self._make_one()
        queue.add(DummyMessage('one'))
        self.assertEqual(len(queue), 1)
        self.failUnless(queue)
        queue.add(DummyMessage('two'))
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.pop_next(), 'one')
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.pop_next(), 'two')
        self.assertEqual(len(queue), 0)
        self.failIf(queue)

    def zztest_is_duplicate_false(self):
        queue = self._make_one()
        message = DummyMessage('one')
        self.failIf(queue.is_duplicate(message))

    def zztest_is_duplicate_bbb_persistence(self):
        queue = self._make_one()
        del queue._message_ids
        message = DummyMessage('one')
        self.failIf(queue.is_duplicate(message))

    def zztest_is_duplicate_true(self):
        queue = self._make_one()
        message = DummyMessage('one')
        queue.add(message)
        self.failUnless(queue.is_duplicate(message))

    def zztest_no_msgid(self):
        queue = self._make_one()
        message = DummyMessage('one')
        del message['Message-Id']
        queue.add(message)
        self.assertEqual(len(queue), 1)
        self.failUnless('Message-Id' in message)

    def zztest_add_msg_error_aborts(self):
        queue = self._make_one()
        message = DummyMessage('one')
        queue._message_ids = None
        self.assertRaises(TypeError, queue.add, message)
        self.failUnless(self.tx.aborted)



class TestQueuedMessage(unittest.TestCase):
    def zztest_it(self):
        from opencore.utilities.mbox import _QueuedMessage
        message = DummyMessage('foobar')
        queued = _QueuedMessage(message)
        self.assertEqual(queued.get(), message)
        queued._v_message = None
        self.assertEqual(queued.get().get_payload(), 'foobar')


    def zztest_non_mailbox_message_add(self):
        from opencore.utilities.mbox import _QueuedMessage
        from email.message import Message
        message = Message()
        self.assertRaises(ValueError, lambda: _QueuedMessage(message))



class DummyLogger(object):
    def __init__(self):
        self.warnings = []
        self.infos = []

    def warn(self, msg):
        self.warnings.append(msg)

    def info(self, msg):
        self.infos.append(msg)


from opencore.utilities.message import MboxMessage
class DummyMessage(MboxMessage):
    def __init__(self, body=None):
        MboxMessage.__init__(self)
        self['From'] = 'Harry'
        self['Message-Id'] = '12345'
        self.set_payload(body)

    def __eq__(self, other):
        return self.get_payload().__eq__(other)


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


class DummyDB(object):
    def __init__(self, dbroot, queues, db_path):
        self.dbroot = dbroot
        self.queues = queues
        self.db_path = db_path.strip('/').split('/')

    def root(self):
        node = self.dbroot
        for name in self.db_path[:-1]:
            node[name] = {}
            node = node[name]
        node[self.db_path[-1]] = self.queues
        return self.dbroot


from repoze.bfg.testing import DummyModel
class RaiseRootException(DummyModel):

    def get(self, id):
        raise KeyError('test error')


class DummyTransaction(object):
    committed = False
    aborted = False

    def commit(self):
        self.committed = True

    def abort(self):
        self.aborted = True

from datetime import datetime
class DummyDatetime(object):
    _now = datetime(2010, 5, 12, 2, 42)

    def __call__(self, *args, **kw):
        return datetime(*args, **kw)

    @property
    def datetime(self):
        return self

    def now(self):
        return self._now

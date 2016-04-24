import unittest

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.ext import testbed

import datetime

from models import Subscription

class TestModels(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()

        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

        ndb.get_context().clear_cache()

    def tearDown(self):
        self.testbed.deactivate()

    def testAddSubscription(self):
        Subscription.add_subscription('user1', 'kw1')
        Subscription.add_subscription('user2', 'kw2')
        Subscription.add_subscription('user1', 'kw2')
        Subscription.add_subscription('user2', 'kw2')

        ret = Subscription.get_active_subscriptions()
        print ret
        self.assertEqual(3, len(ret))


if __name__ == '__main__':
    unittest.main()


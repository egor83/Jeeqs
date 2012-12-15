import unittest
from google.appengine.ext import testbed
from google.appengine.api import users
from google.appengine.datastore import datastore_stub_util

from models import *

class JeeqsTestCase(unittest.TestCase):
  def loginExampleUser(self):
    self.testbed.setup_env(
      USER_EMAIL = 'test@example.com',
      USER_ID = '123',
      USER_IS_ADMIN = '1',
      overwrite = True)

  def loginUser(self, email, id, is_admin=False):
    self.testbed.setup_env(
      USER_EMAIL = email,
      USER_ID = id,
      USER_IS_ADMIN = '1' if is_admin else '0',
      overwrite = True)

  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
    self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
    self.testbed.init_user_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_taskqueue_stub()

  def tearDown(self):
    self.testbed.deactivate()

  def testLoginExampleUser(self):
    self.loginExampleUser()
    self.assertIsNotNone(users.get_current_user())

  def CreateChallenge(self, name_persistent="Challenge X"):
    """Creates and returns a new challenge."""
    challenge = Challenge(name_persistent=name_persistent)
    challenge.put()
    return challenge

  def CreateJeeqser(self, email="random@wrong_domain.com"):
    """Creates and returns a new Jeeqser object."""
    jeeqser = Jeeqser(user=users.User(email=email))
    jeeqser.put()
    return jeeqser

if __name__ == '__main__':
  unittest.main()
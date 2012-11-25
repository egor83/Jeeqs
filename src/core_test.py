import unittest
from google.appengine.ext import testbed
from google.appengine.api import users

class CoreTestCase(unittest.TestCase):
  def loginExampleUser(self):
    self.testbed.setup_env(
      USER_EMAIL = 'test@example.com',
      USER_ID = '123',
      USER_IS_ADMIN = '1',
      overwrite = True)

  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_user_stub()

  def tearDown(self):
    self.testbed.deactivate()

  def testLoginExampleUser(self):
    self.loginExampleUser()
    self.assertIsNotNone(users.get_current_user())

if __name__ == '__main__':
  unittest.main()
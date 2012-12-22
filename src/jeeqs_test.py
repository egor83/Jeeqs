#!/usr/bin/python
import mox
import optparse
import program_handler
import sys
import traceback
import unittest
import unittest2
import webapp2
import webtest

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
    self.mox = mox.Mox()

  def tearDown(self):
    self.testbed.deactivate()
    self.mox.UnsetStubs()

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

class ProgramHandlerTestCase(JeeqsTestCase):

  def setUp(self):
    JeeqsTestCase.setUp(self)
    app = webapp2.WSGIApplication([('/challenge/shell.runProgram', program_handler.ProgramHandler)])
    self.testapp = webtest.TestApp(app)

  def tearDown(self):
    JeeqsTestCase.tearDown(self)

  def test_program_handler_print(self):
    program = """
print 1
    """
    params = {
      'program': program
    }
    try:
      response = self.testapp.get('/challenge/shell.runProgram', params)
    except Exception as ex:
      self.fail(traceback.print_exc())
    self.assertTrue('1' in response.body)
    self.assertTrue('200' in response.status)

USAGE = """%prog SDK_PATH TEST_PATH
Run unit tests for App Engine apps.

SDK_PATH    Path to the SDK installation
TEST_PATH   Path to package containing test modules"""


def main(sdk_path, test_path):
  sys.path.insert(0, sdk_path)
  import dev_appserver
  dev_appserver.fix_sys_path()
  suite = unittest2.loader.TestLoader().discover(test_path, pattern="*_test.py")
  unittest2.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
  #  unittest.main()
  parser = optparse.OptionParser(USAGE)
  options, args = parser.parse_args()
  if len(args) != 2:
    print 'Error: Exactly 2 arguments required.'
    parser.print_help()
    sys.exit(1)
  SDK_PATH = args[0]
  TEST_PATH = args[1]
  main(SDK_PATH, TEST_PATH)


import unittest
from google.appengine.ext import testbed
from google.appengine.api import users

import jeeqs_test

class CoreTestCase(jeeqs_test.JeeqsTestCase):
  def setUp(self):
    jeeqs_test.JeeqsTestCase.setUp(self)

  def tearDown(self):
    jeeqs_test.JeeqsTestCase.tearDown(self)

  def testXYZ(self):
    pass

if __name__ == '__main__':
  unittest.main()
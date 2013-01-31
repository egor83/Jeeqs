import unittest
from google.appengine.ext import testbed
from google.appengine.api import users

import test_jeeqs

class CoreTestCase(test_jeeqs.JeeqsTestCase):
  def setUp(self):
      test_jeeqs.JeeqsTestCase.setUp(self)

  def tearDown(self):
      test_jeeqs.JeeqsTestCase.tearDown(self)

  def testXYZ(self):
    pass

if __name__ == '__main__':
  unittest.main()
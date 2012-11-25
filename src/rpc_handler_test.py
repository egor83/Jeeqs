import unittest
import jeeqs_test
from google.appengine.api import users
import webapp2
import webtest
from rpc_handler import RPCHandler

from models import *

class RPCHandlerTestCase(jeeqs_test.JeeqsTestCase):

  def setUp(self):
    jeeqs_test.JeeqsTestCase.setUp(self)
    app = webapp2.WSGIApplication([('/rpc', RPCHandler)])
    self.testapp = webtest.TestApp(app)

  def tearDown(self):
    jeeqs_test.JeeqsTestCase.tearDown(self)

  def testSubmitVote(self):
    challenge = Challenge(name_persistent="Challenge X")
    challenge.put()

    submitter = Jeeqser(user=users.User(email="random@wrong_domain.com"))
    submitter.put()

    submitter_challenge = Jeeqser_Challenge(parent=submitter.key, challenge=challenge.key, jeeqser=submitter.key)
    submitter_challenge.put()

    voter = Jeeqser(user=users.User(email="voter@wrong_domain.com"))
    voter.put()

    submission = Attempt(author=submitter.key, challenge=challenge.key)
    submission.put()

    # Qualify the voter
    voter_challenge = Jeeqser_Challenge(parent=voter.key, challenge=challenge.key, jeeqser=voter.key, status=AttemptStatus.SUCCESS)
    voter_challenge.put()

    self.loginUser('voter@wrong_domain.com', 'voter')

    params = {'method': 'submitVote', 'submission_key': submission.key.urlsafe(), 'vote': Vote.CORRECT}
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      self.fail()

    submission, challenge, submitter_challenge, submitter, voter = ndb.get_multi(
        [submission.key,
        challenge.key,
        submitter_challenge.key,
        submitter.key,
        voter.key])

    self.assertEquals(submitter_challenge.status, AttemptStatus.SUCCESS)
    self.assertEquals(submission.status, AttemptStatus.SUCCESS)
    self.assertEquals(submission.correct_count, 1)
    self.assertEquals(submission.incorrect_count, 0)
    self.assertEquals(submitter.correct_submissions_count, 1)
    self.assertEquals(voter.reviews_out_num, 1)
    self.assertEquals(submitter.reviews_in_num, 1)


if __name__ == '__main__':
  unittest.main()
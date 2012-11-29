import traceback
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

  def testFirstSubmitAttempt(self):
    """Tests a first submission to a challenge."""
    challenge = self.CreateChallenge()
    submitter_email = "submitter@wrong_domain.com"
    submitter = self.CreateJeeqser(email=submitter_email)
    solution = 'Dummy solution!'
    self.loginUser(submitter_email, 'submitter')
    params = {
        'method' : 'submitAttempt',
        'solution' : solution,
        'challenge_key' : challenge.key
        }
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      self.fail(traceback.format_exception(ex))
      raise

  def testSubmitFirstCorrectVote(self):
    """Tests submitting a first correct vote to a submission."""
    challenge = self.CreateChallenge()
    submitter = self.CreateJeeqser()
    submitter_challenge = Jeeqser_Challenge(parent=submitter.key, challenge=challenge.key, jeeqser=submitter.key)
    submitter_challenge.put()
    voter = self.CreateJeeqser(email="voter@wrong_domain.com")
    submission = Attempt(author=submitter.key, challenge=challenge.key)
    submission.put()
    # Qualify the voter
    voter_challenge = Jeeqser_Challenge(parent=voter.key, challenge=challenge.key, jeeqser=voter.key, status=AttemptStatus.SUCCESS)
    voter_challenge.put()
    self.loginUser('voter@wrong_domain.com', 'voter')
    params = {
        'method': 'submitVote',
        'submission_key': submission.key.urlsafe(),
        'vote': Vote.CORRECT}
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      self.fail(traceback.format_exception(ex))
      raise

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
    self.assertEquals(challenge.num_jeeqsers_solved, 1)
    self.assertEquals(challenge.last_solver, submitter.key)
    # TODO query for the feedback
    # TODO query for the activity


if __name__ == '__main__':
  unittest.main()
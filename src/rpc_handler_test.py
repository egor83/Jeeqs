import traceback
import unittest
import jeeqs_test
from google.appengine.api import users
import webapp2
import webtest
from rpc_handler import RPCHandler

from models import *

VOTER_EMAIL = 'voter@wrong_domain.com'
SUBMITTER_EMAIL = "submitter@nonexistent_domain.com"

class RPCHandlerTestCase(jeeqs_test.JeeqsTestCase):

  def setUp(self):
    jeeqs_test.JeeqsTestCase.setUp(self)
    app = webapp2.WSGIApplication([('/rpc', RPCHandler)])
    self.testapp = webtest.TestApp(app)

  def tearDown(self):
    jeeqs_test.JeeqsTestCase.tearDown(self)

  def testSubmitFirstCorrectVote(self):
    """Tests submitting a first correct vote to a submission."""
    challenge = self.CreateChallenge()
    submitter = self.CreateJeeqser()
    submitter_challenge = Jeeqser_Challenge(parent=submitter.key, challenge=challenge.key, jeeqser=submitter.key)
    submitter_challenge.put()
    voter = self.CreateJeeqser(email=VOTER_EMAIL)
    submission = Attempt(author=submitter.key, challenge=challenge.key)
    submission.put()
    # Qualify the voter
    voter_challenge = Jeeqser_Challenge(parent=voter.key, challenge=challenge.key, jeeqser=voter.key, status=AttemptStatus.SUCCESS)
    voter_challenge.put()
    self.loginUser(VOTER_EMAIL, 'voter')
    params = {
        'method': 'submitVote',
        'submission_key': submission.key.urlsafe(),
        'vote': Vote.CORRECT}
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      self.fail(traceback.print_exc())

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

  def testSubmitFirstAttempt(self):
    """Tests submitting a first attempt to a challenge."""
    challenge = self.CreateChallenge()
    submitter = self.CreateJeeqser(email=SUBMITTER_EMAIL)
    solution = "blahblahblah"
    self.loginUser(SUBMITTER_EMAIL, 'submitter')
    params = {
      'method': 'submitAttempt',
      'challenge_key': challenge.key.urlsafe(),
      'solution': solution}
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      traceback.print_exc()
      self.fail()

    challenge, submitter = ndb.get_multi(
      [challenge.key,
       submitter.key])
    self.assertEquals(challenge.num_jeeqsers_submitted, 1)
    self.assertEquals(submitter.submissions_num, 1)
    submitter_challenge_list = Jeeqser_Challenge.query(ancestor=submitter.key).filter(
      Jeeqser_Challenge.challenge==challenge.key).fetch(1)
    self.assertEquals(len(submitter_challenge_list), 1)
    self.assertEquals(submitter_challenge_list[0].jeeqser, submitter.key)
    self.assertIsNone(submitter_challenge_list[0].status)

  def testSubmitAttemptAutomaticChallenge(self):
    challenge = self.CreateChallenge()
    challenge.automatic_review = True
    challenge.put()
    submitter = self.CreateJeeqser(email=SUBMITTER_EMAIL)
    solution = "blahblahblah"
    self.loginUser(SUBMITTER_EMAIL, 'submitter')
    params = {
      'method': 'submitAttempt',
      'challenge_key': challenge.key.urlsafe(),
      'solution': solution}
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      traceback.print_exc()
      self.fail()

if __name__ == '__main__':
  unittest.main()
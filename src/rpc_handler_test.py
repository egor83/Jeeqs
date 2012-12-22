import traceback
import unittest
import jeeqs_test
import json
import mox
import rpc_handler
import spam_manager
import webapp2
import webtest

from google.appengine.ext import deferred
from models import *

VOTER_EMAIL = 'voter@wrong_domain.com'
SUBMITTER_EMAIL = "submitter@nonexistent_domain.com"
USER_A_EMAIL = 'user_a@wrong_domain.com'

class RPCHandlerTestCase(jeeqs_test.JeeqsTestCase):

  def setUp(self):
    jeeqs_test.JeeqsTestCase.setUp(self)
    app = webapp2.WSGIApplication([('/rpc', rpc_handler.RPCHandler)])
    self.testapp = webtest.TestApp(app)

  def tearDown(self):
    jeeqs_test.JeeqsTestCase.tearDown(self)

  def test_submit_first_correct_vote(self):
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
        'method': 'submit_vote',
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
    self.assertTrue(len(Feedback.query(ancestor=submission.key).fetch(1)) > 0)
    self.assertTrue(len(Activity.query(ancestor=voter.key).fetch(1)) > 0)

  def test_submit_first_attempt(self):
    """Tests submitting a first attempt to a challenge."""
    challenge = self.CreateChallenge()
    submitter = self.CreateJeeqser(email=SUBMITTER_EMAIL)
    solution = "blahblahblah"
    self.loginUser(SUBMITTER_EMAIL, 'submitter')
    params = {
        'method': 'submit_attempt',
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

  def test_submit_attempt_automatic_challenge(self):
    challenge = self.CreateChallenge()
    challenge.automatic_review = True
    challenge.put()
    solution = "blahblahblah"
    self.loginUser(SUBMITTER_EMAIL, 'submitter')
    self.mox.StubOutWithMock(deferred, 'defer')
    deferred.defer(
        rpc_handler.handleAutomaticReview,
        mox.IgnoreArg(),
        challenge.key.urlsafe(),
        mox.IgnoreArg(),
        mox.IgnoreArg())
    self.mox.ReplayAll()
    params = {
        'method': 'submit_attempt',
        'challenge_key': challenge.key.urlsafe(),
        'solution': solution}
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      traceback.print_exc()
      self.fail()
    self.mox.VerifyAll()

  def test_save_draft(self):
    challenge = self.CreateChallenge()
    draft = "draft solution text"
    submitter = self.CreateJeeqser(email=SUBMITTER_EMAIL)
    self.loginUser(SUBMITTER_EMAIL, 'submitter')
    params = {
        'method' : 'save_draft_solution',
        'solution': draft,
        'challenge_key' : challenge.key.urlsafe()
    }
    try:
      self.testapp.post('/rpc', params)
    except Exception as ex:
      traceback.print_exc()
      self.fail()
    drafts = Draft.query().filter(
      Draft.challenge==challenge.key,
      Draft.author==submitter.key
    ).fetch()
    self.assertEquals(len(drafts), 1)
    self.assertEquals(drafts[0].markdown, draft)

  def test_flag_feedback(self):
    submitter = self.CreateJeeqser()
    flagger = self.CreateJeeqser(email=USER_A_EMAIL)
    self.loginUser(USER_A_EMAIL, 'flagger')
    challenge = self.CreateChallenge()
    attempt = Attempt(author=submitter.key, challenge=challenge.key)
    attempt.put()
    feedback = Feedback(parent=attempt.key, attempt=attempt.key, author=flagger.key)
    feedback.put()
    params = {
        'method' : 'flag_feedback',
        'feedback_key' : feedback.key.urlsafe()
    }
    try:
      response = self.testapp.post('/rpc', params)
      # refresh feedback
      feedback = feedback.key.get()
      self.assertTrue(flagger.key in feedback.flagged_by)
      self.assertEquals(
          json.loads(response.body)['flags_left_today'],
          spam_manager.SpamManager.FLAGGING_LIMIT_PER_DAY - 1)
    except Exception as ex:
      traceback.print_exc()
      self.fail()

if __name__ == '__main__':
  unittest.main()
import traceback
import unittest
import test_jeeqs
import json
import mox
import rpc_handler
import spam_manager
import webapp2
import webtest

from google.appengine.ext import deferred
from models import *

REVIEWER_EMAIL = 'reviewer@wrong_domain.com'
SUBMITTER_EMAIL = "submitter@nonexistent_domain.com"
USER_A_EMAIL = 'user_a@wrong_domain.com'
UPVOTER_EMAIL = 'upvoter@wrong_domain.com'
DOWNVOTER_EMAIL = 'downvoter@wrong_domain.com'


class RPCHandlerTestCase(test_jeeqs.JeeqsTestCase):

    def setUp(self):
        test_jeeqs.JeeqsTestCase.setUp(self)
        app = webapp2.WSGIApplication([('/rpc', rpc_handler.RPCHandler)])
        self.testapp = webtest.TestApp(app)

    def tearDown(self):
        test_jeeqs.JeeqsTestCase.tearDown(self)

    def create_submitter_challenge(self):
        challenge = self.CreateChallenge()
        submitter = self.CreateJeeqser()
        submitter_challenge = Jeeqser_Challenge(parent=submitter.key,
                                                challenge=challenge.key,
                                                jeeqser=submitter.key)
        submitter_challenge.put()
        submission = Attempt(author=submitter.key, challenge=challenge.key)
        submission.put()
        return challenge, submission, submitter, submitter_challenge

    def test_review_qualification(self):
        """Review as a non-qualified reviewer

        and verify that we don't persist the review.

        """
        pass

    def test_submit_first_correct_review(self):
        """Tests submitting a first correct review to a submission."""
        (
            challenge, submission, submitter, submitter_challenge) = \
            self.create_submitter_challenge()
        # Qualify the reviewer
        reviewer = self.CreateJeeqser(email=REVIEWER_EMAIL)
        reviewer_challenge = Jeeqser_Challenge(parent=reviewer.key,
                                               challenge=challenge.key,
                                               jeeqser=reviewer.key,
                                               status=AttemptStatus.SUCCESS)
        reviewer_challenge.put()
        self.loginUser(REVIEWER_EMAIL, 'reviewer')
        params = {
            'method': 'submit_review',
            'submission_key': submission.key.urlsafe(),
            'review': Review.CORRECT}
        try:
            self.testapp.post('/rpc', params)
        except Exception as ex:
            self.fail(traceback.print_exc())

        submission, challenge, submitter_challenge, submitter, reviewer = \
            ndb.get_multi([
                submission.key,
                challenge.key,
                submitter_challenge.key,
                submitter.key,
                reviewer.key])

        self.assertEquals(submitter_challenge.status, AttemptStatus.SUCCESS)
        self.assertEquals(submission.status, AttemptStatus.SUCCESS)
        self.assertEquals(submission.correct_count, 1)
        self.assertEquals(submission.incorrect_count, 0)
        self.assertEquals(submitter.correct_submissions_count, 1)
        self.assertEquals(reviewer.reviews_out_num, 1)
        self.assertEquals(submitter.reviews_in_num, 1)
        self.assertEquals(challenge.num_jeeqsers_solved, 1)
        self.assertEquals(challenge.last_solver, submitter.key)
        self.assertTrue(len(Feedback.query(
            ancestor=submission.key).fetch(1)) > 0)
        self.assertTrue(len(Activity.query(
            ancestor=reviewer.key).fetch(1)) > 0)

    def test_flag_attempt(self):
        """Tests reviewer adding a flag for a submission"""
        (challenge, submission, submitter, submitter_challenge) = \
            self.create_submitter_challenge()
        # Qualify a number of reviewers
        reviewers = []
        for reviewer_index in range(
                spam_manager.SpamManager.SUBMISSION_FLAG_THRESHOLD):
            reviewer = self.CreateJeeqser(email=REVIEWER_EMAIL
                                          + str(reviewer_index))
            reviewer_challenge = Jeeqser_Challenge(
                parent=reviewer.key,
                challenge=challenge.key,
                jeeqser=reviewer.key,
                status=AttemptStatus.SUCCESS)
            reviewer_challenge.put()
            reviewers.append(reviewer)

        self.loginUser(REVIEWER_EMAIL, 'reviewer')
        params = {
            'method': 'submit_review',
            'submission_key': submission.key.urlsafe(),
            'review': Review.FLAG}
        for reviewer in reviewers:
            self.loginUser(REVIEWER_EMAIL + str(reviewer_index),
                           'reviewer' + str(reviewer_index))
            try:
                self.testapp.post('/rpc', params)
            except Exception as ex:
                self.fail(traceback.print_exc())
        submission = submission.key.get()
        self.assertTrue(submission.flagged)

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

        challenge, submitter = ndb.get_multi([challenge.key, submitter.key])
        self.assertEquals(challenge.num_jeeqsers_submitted, 1)
        self.assertEquals(submitter.submissions_num, 1)
        submitter_challenge_list = Jeeqser_Challenge.query(
            ancestor=submitter.key).filter(
                Jeeqser_Challenge.challenge == challenge.key).fetch(1)
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
            rpc_handler.handle_automatic_review,
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
            'method': 'save_draft_solution',
            'solution': draft,
            'challenge_key': challenge.key.urlsafe()
        }
        try:
            self.testapp.post('/rpc', params)
        except Exception as ex:
            traceback.print_exc()
            self.fail()
        drafts = Draft.query().filter(
            Draft.challenge == challenge.key,
            Draft.author == submitter.key
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
        feedback = Feedback(parent=attempt.key, attempt=attempt.key,
                            author=flagger.key)
        feedback.put()
        params = {
            'method': 'flag_feedback',
            'feedback_key': feedback.key.urlsafe()
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

    def test_update_displayname(self):
        reviewer = self.CreateJeeqser(email=REVIEWER_EMAIL)
        self.loginUser(REVIEWER_EMAIL, 'reviewer')
        try:
            #update to an available display name
            params = {
                'method': 'update_displayname',
                'displayname': 'noob'}
            response = self.testapp.post('/rpc', params)
            self.assertEquals('success', response.body,
                              'display name not getting updated')
            #update to own display name
            params = {
                'method': 'update_displayname',
                'displayname': 'noob'}
            response = self.testapp.post('/rpc', params)
            self.assertEquals('no_operation', response.body,
                              'no operation failed')
            # update to already taken display name
            # display name 'noob' has already been taken
            # by user 'reviewer' above
            userA = self.CreateJeeqser(email=USER_A_EMAIL)
            self.loginUser(USER_A_EMAIL, 'userA')
            params = {
                'method': 'update_displayname',
                'displayname': 'noob'}
            response = self.testapp.post('/rpc', params)
            self.assertEquals('not_unique', response.body, 'not_unique failed')
        except Exception as ex:
            self.fail(traceback.print_exc())

    def test_submit_upvote(self):
        """Test upvoting.

        Check total score, check that voter is in the list of upvoters
        and not in the list of downvoters.

        """

        challenge, submission, submitter, submitter_challenge = \
            self.create_submitter_challenge()

        upvoter = self.CreateJeeqser(UPVOTER_EMAIL)
        self.loginUser(UPVOTER_EMAIL, 'upvoter')

        upvote_params = {
            'method': 'submit_vote',
            'submission': submission.key.urlsafe(),
            'direction': Attempt.IS_UPVOTED,
            'original_vote': 'null'
        }
        try:
            self.testapp.post('/rpc', upvote_params)
        except Exception as ex:
            traceback.print_exc()
            self.fail()

        # refresh the submission to get a vote
        submission = submission.key.get()
        self.assertEqual(submission.votes_total, 1)
        self.assertTrue(upvoter.key in submission.upvoted)
        self.assertEqual(len(submission.upvoted), 1)
        self.assertFalse(upvoter.key in submission.downvoted)
        self.assertEqual(len(submission.downvoted), 0)

    def test_submit_downvote(self):
        """Test downvoting.

        Check total score, check that voter is in the list of downvoters
        and not in the list of upvoters.

        """

        challenge, submission, submitter, submitter_challenge = \
            self.create_submitter_challenge()

        downvoter = self.CreateJeeqser(DOWNVOTER_EMAIL)
        self.loginUser(DOWNVOTER_EMAIL, 'downvoter')

        downvote_params = {
            'method': 'submit_vote',
            'submission': submission.key.urlsafe(),
            'direction': Attempt.IS_DOWNVOTED,
            'original_vote': 'null'
        }
        try:
            self.testapp.post('/rpc', downvote_params)
        except Exception as ex:
            traceback.print_exc()
            self.fail()

        # refresh the submission to get a vote
        submission = submission.key.get()
        self.assertEqual(submission.votes_total, -1)
        self.assertFalse(downvoter.key in submission.upvoted)
        self.assertEqual(len(submission.upvoted), 0)
        self.assertTrue(downvoter.key in submission.downvoted)
        self.assertEqual(len(submission.downvoted), 1)

    def change_vote(self):
        """Test changing downvote to upvote.

        Check score, presence in up/downvoters' list.

        """

        challenge, submission, submitter, submitter_challenge = \
            self.create_submitter_challenge()

        downvoter = self.CreateJeeqser(DOWNVOTER_EMAIL)
        self.loginUser(DOWNVOTER_EMAIL, 'downvoter')

        downvote_params = {
            'method': 'submit_vote',
            'submission': submission.key.urlsafe(),
            'direction': Attempt.IS_DOWNVOTED,
            'original_vote': 'null'
        }
        try:
            self.testapp.post('/rpc', downvote_params)
        except Exception as ex:
            traceback.print_exc()
            self.fail()

        new_upvote_params = {
            'method': 'submit_vote',
            'submission': submission.key.urlsafe(),
            'direction': Attempt.IS_UPVOTED,
            'original_vote': Attempt.IS_DOWNVOTED
        }

        try:
            self.testapp.post('/rpc', new_upvote_params)
        except Exception as ex:
            traceback.print_exc()
            self.fail()

        # refresh the submission to get a vote
        submission = submission.key.get()
        self.assertEqual(submission.votes_total, 1)
        self.assertTrue(downvoter.key in submission.upvoted)
        self.assertEqual(len(submission.upvoted), 1)
        self.assertFalse(downvoter.key in submission.downvoted)
        self.assertEqual(len(submission.downvoted), 0)

    def test_anonymous_voting(self):
        upvote_params = {
            'method': 'submit_vote',
            'submission': '',
            'direction': Attempt.IS_UPVOTED,
            'original_vote': 'null'
        }
        try:
            self.assertRaises(webtest.AppError, self.testapp.post, ('/rpc'), {'params': upvote_params})
        except Exception as ex:
            traceback.print_exc()
            self.fail()


if __name__ == '__main__':
    unittest.main()

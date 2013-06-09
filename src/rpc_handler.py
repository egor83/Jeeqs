from models import *
import core
import status_code
import logging
import json
import spam_manager
import program_tester
import datetime
import lib.markdown as markdown
from google.appengine.api import users
from google.appengine.ext import deferred
import jeeqs_request_handler
import jeeqs_exceptions
import paging_handler


class RPCHandler(jeeqs_request_handler.JeeqsRequestHandler):
    """Handles RPC calls
    """

    @core.authenticate(True)
    def post(self):
        method = self.request.get('method')
        if (not method):
            self.error(status_code.StatusCode.forbidden)
            return

        if method == 'submit_review':
            self.submit_review()
        elif method == 'update_displayname':
            self.update_displayname()
        elif method == 'update_profile_picture':
            self.update_profile_picture()
        elif method == 'submit_attempt':
            self.submit_attempt()
        elif method == 'save_draft_solution':
            self.save_draft_solution()
        elif method == 'flag_feedback':
            self.flag_feedback()
        elif method == 'submit_challenge_source':
            self.submit_challenge_source()
        elif method == 'submit_challenge_vertical_scroll':
            self.submit_challenge_vertical_scroll()
        elif method == 'took_tour':
            self.took_tour()
        elif method == 'submit_vote':
            self.submit_vote()
        else:
            self.error(status_code.StatusCode.forbidden)
            return

    def get(self):
        method = self.request.get('method')
        logging.debug("dispatching method %s " % method)
        if (not method):
            self.error(status_code.StatusCode.forbidden)
            return
        if method == 'get_in_jeeqs':
            self.get_in_jeeqs()
        elif method == 'get_challenge_avatars':
            self.get_challenge_avatars()
        elif method == 'get_activities':
            self.get_activities()
        elif method == 'get_feedbacks':
            self.get_feedbacks()
        elif method == 'get_feedbacks_for_submissoin':
            self.get_feedbacks_for_submissoin()
        else:
            self.error(status_code.StatusCode.forbidden)
            return

    @staticmethod
    def get_review_numeric_value(review):
        if review == Review.CORRECT:
            return 2
        elif review == Review.INCORRECT:
            return 0
        else:
            return 0  # flag

    @staticmethod
    def apply_new_status(jeeqser_challenge, previous_status, submission):
        if jeeqser_challenge.status != previous_status:
            jeeqser_challenge.status_changed_on = datetime.datetime.now()

            if jeeqser_challenge.status == AttemptStatus.SUCCESS:
                # TODO: This may not scale since challenge's entity group is
                # high traffic - use sharded counters
                submission.challenge.get().num_jeeqsers_solved += 1
                submission.challenge.get(
                ).update_last_solver(submission.author.get())
                submission.author.get().correct_submissions_count += 1

            elif jeeqser_challenge.status == AttemptStatus.FAIL:
                if previous_status == AttemptStatus.SUCCESS:
                    submission.challenge.get().num_jeeqsers_solved -= 1
                    submission.author.get().correct_submissions_count -= 1
                last_solver = submission.challenge.get().last_solver
                if (last_solver and last_solver == submission.author):
                    submission.challenge.get().update_last_solver(None)

    @staticmethod
    def update_graph_for_review(
            submission, jeeqser_challenge, review, reviewer):
        """
        Updates the object graph based on the review given by the reviewer
        :param submission: The submission for which the review is given
        :param jeeqser_challenge:  The corresponding jeeqser_challenge entity
        :param review: the review given
        :param reviewer: the reviewer
        """
        submission.users_reviewed.append(reviewer.key)
        submission.review_count += 1
        submission.feedback_score_sum += float(
            RPCHandler.get_review_numeric_value(review))
        submission.feedback_score_average = float(
            submission.feedback_score_sum / submission.review_count)
        if submission.review_count == 1:
            submission.challenge.get().submissions_without_review -= 1
        reviewer.reviews_out_num += 1
        submission.author.get().reviews_in_num += 1

        if review == Review.CORRECT:
            submission.correct_count += 1
            jeeqser_challenge.correct_count = submission.correct_count
        elif review == Review.INCORRECT:
            submission.incorrect_count += 1
            jeeqser_challenge.incorrect_count = submission.incorrect_count
        elif review == Review.FLAG:
            submission.flag_count += 1
            jeeqser_challenge.flag_count = submission.flag_count
            if (
                submission.flag_count >=
                spam_manager.SpamManager.SUBMISSION_FLAG_THRESHOLD) or\
                reviewer.is_moderator or\
                    users.is_current_user_admin():
                submission.flagged = True
                spam_manager.SpamManager.flag_author(submission.author.get())
            submission.flagged_by.append(reviewer.key)

        previous_status = jeeqser_challenge.status
        if submission.correct_count > (
                submission.incorrect_count + submission.flag_count):
            jeeqser_challenge.status = AttemptStatus.SUCCESS
            submission.status = jeeqser_challenge.status
        else:
            submission.status = jeeqser_challenge.status = AttemptStatus.FAIL

        RPCHandler.apply_new_status(
            jeeqser_challenge, previous_status, submission)

    @core.authenticate(False)
    def get_activities(self):
        cursor = self.request.get('cursor')
        all_activities = Activity.query().order(-Activity.date)

        if cursor == '':
            activities_for_page, cursor, more = all_activities.fetch_page(10)
            qo = ndb.QueryOptions(
                start_cursor=ndb.Cursor(urlsafe=cursor.to_websafe_string()))
            activities_for_page, cursor, more = \
                all_activities.fetch_page(10, options=qo)
        else:
            qo = ndb.QueryOptions(start_cursor=ndb.Cursor(urlsafe=cursor))
            activities_for_page, cursor, more = \
                all_activities.fetch_page(10, options=qo)

        vars = core.add_common_vars({'activities': activities_for_page})
        template = core.jinja_environment.get_template('activities_list.html')
        rendered = template.render(vars)
        json_response = json.dumps({'cursor': cursor.to_websafe_string(),
                                    'activities': rendered, 'more': more})
        self.response.write(json_response)

    @core.authenticate(False)
    def get_in_jeeqs(self):
        submission_key = self.request.get('submission_key')

        submission = None

        try:
            submission = ndb.Key(urlsafe=submission_key).get()
        finally:
            if not submission:
                self.error(status_code.StatusCode.forbidden)
                return

        # TODO: We can optimize these kind of calls by never retrieving
        # submission object
        feedbacks = Feedback.query()\
            .filter(Feedback.attempt == submission.key)\
            .filter(Feedback.flagged == False)\
            .order(Feedback.flag_count)\
            .order(-Feedback.date)\
            .fetch(10)

        if feedbacks:
            core.prettify_injeeqs(feedbacks)

        vars = core.add_common_vars({
            'feedbacks': feedbacks,
            'jeeqser': self.jeeqser
        })

        template = core.jinja_environment.get_template('in_jeeqs_list.html')
        rendered = template.render(vars)
        self.response.write(rendered)

    @core.authenticate(False)
    def get_feedbacks(self):
        fph = paging_handler.FeedbacksPagingHandler(self.request)
        submission = self.request.get('submission')

        if submission:
            submission = ndb.Key(urlsafe=submission)
            feedbacks, cursor, has_newer = \
                fph.get_feedbacks_for_submission(self.jeeqser.key, submission)
        else:
            feedbacks, cursor, has_newer = \
                fph.get_feedbacks_for_feeqser(self.jeeqser.key)

        vars = core.add_common_vars({
            'jeeqser': self.jeeqser,
            'feedbacks': feedbacks,
            'cursor': cursor,
            'has_newer': has_newer,
            'write_challenge_name': True
        })

        template = core.jinja_environment.get_template('in_jeeqs_list.html')
        rendered = template.render(vars)
        self.response.write(rendered)

    def submit_challenge_vertical_scroll(self):
        """updates a challenge's source url """
        if not users.is_current_user_admin():
            self.error(status_code.StatusCode.unauth)
            return

        new_vertical_scroll = self.request.get('vertical_scroll')
        if not new_vertical_scroll:
            self.error(status_code.StatusCode.forbidden)
            return

        # retrieve the challenge
        challenge_key = self.request.get('challenge_key')
        if not challenge_key:
            self.error(status_code.StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = Challenge.get(challenge_key)
        finally:
            if not challenge:
                self.error(status_code.StatusCode.forbidden)
                return

        challenge.vertical_scroll = float(new_vertical_scroll)
        challenge.put()

    def submit_challenge_source(self):
        """updates a challenge's source """
        if not users.is_current_user_admin():
            self.error(status_code.StatusCode.unauth)
            return

        new_source = self.request.get('source')
        if not new_source:
            self.error(status_code.StatusCode.forbidden)
            return

        # retrieve the challenge
        challenge_key = self.request.get('challenge_key')
        if not challenge_key:
            self.error(status_code.StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = Challenge.get(challenge_key)
        finally:
            if not challenge:
                self.error(status_code.StatusCode.forbidden)
                return

        challenge.markdown = new_source
        challenge.content = markdown.markdown(
            challenge.markdown, ['codehilite', 'mathjax'])
        challenge.put()

    def append_language_prefix_for_automatic_review(self, challenge, solution):
        """Appends the proper language prefix"""
        if challenge.automatic_review:
            new_solution = '    :::python' + '\n'
            for line in solution.splitlines(True):
                new_solution += '    ' + line
            return new_solution
        return solution

    @ndb.transactional(xg=True)
    def persistAttempt(self, challenge_key, solution):
        """persists new attempt."""
        self.jeeqser, challenge = ndb.get_multi(
            [self.jeeqser.key, challenge_key])

        jeeqser_challenge = get_jeeqser_challenge(
            self.jeeqser.key, challenge_key)
        previous_index = 0
        if jeeqser_challenge:
            previous_index = jeeqser_challenge.active_attempt.get().index
            jeeqser_challenge.active_attempt.get().active = False
            jeeqser_challenge.active_attempt.get().put()
            if jeeqser_challenge.status == AttemptStatus.SUCCESS:
                challenge.num_jeeqsers_solved -= 1
        else:
            jeeqser_challenge = Jeeqser_Challenge(
                parent=self.jeeqser.key,
                jeeqser=self.jeeqser.key,
                challenge=challenge_key
            )
            challenge.num_jeeqsers_submitted += 1
        challenge.submissions_without_review += 1

        challenge.put()
        attempt = Attempt(
            parent=self.jeeqser.key,
            author=self.jeeqser.key,
            challenge=challenge_key,
            content=markdown.markdown(solution, ['codehilite', 'mathjax']),
            markdown=solution,
            active=True,
            index=previous_index + 1)
        attempt.put()

        if jeeqser_challenge.status == AttemptStatus.SUCCESS:
            self.jeeqser.correct_submissions_count -= 1

        jeeqser_challenge.active_attempt = attempt.key
        jeeqser_challenge.incorrect_count = jeeqser_challenge.flag_count = 0
        jeeqser_challenge.correct_count = 0
        jeeqser_challenge.status = None
        jeeqser_challenge.put()

        self.jeeqser.submissions_num += 1
        self.jeeqser.put()

        Activity(
            type='submission',
            done_by=self.jeeqser.key,
            done_by_displayname=self.jeeqser.displayname,
            done_by_gravatar=self.jeeqser.profile_url,
            challenge=challenge.key,
            challenge_name=challenge.name).put()

        return self.jeeqser, attempt, jeeqser_challenge

    def submit_attempt(self):
        """
        Submits a solution
        """
        program = solution = self.getValueInQuery('solution')
        challenge_key = ndb.Key(urlsafe=self.getValueInQuery('challenge_key'))
        # no need to test if challenge exists,
        # since if it doesn't we will throw here and
        # the upper stream will convert the exception to user output
        challenge = challenge_key.get()
        solution = self.append_language_prefix_for_automatic_review(
            challenge, solution)
        self.jeeqser, attempt, jeeqser_challenge = self.persistAttempt(
            challenge_key, solution)

        # delete a draft if exists
        draft = Draft.query(ancestor=self.jeeqser.key).filter(
            Draft.challenge == challenge_key).fetch(1)
        if draft and len(draft) > 0:
            draft[0].key.delete()

        if challenge.automatic_review:
            deferred.defer(
                handle_automatic_review,
                attempt.key.urlsafe(),
                challenge.key.urlsafe(),
                jeeqser_challenge.key.urlsafe(),
                program)

    def save_draft_solution(self):
        """
        Submits a solution
        """
        solution = self.getValueInQuery('solution')
        challenge_key = self.getValueInQuery('challenge_key')
        challenge_key = ndb.Key(urlsafe=challenge_key)

        @ndb.transactional(xg=True)
        def persist_new_draft():
            try:
                draft = Draft.query(
                    ancestor=self.jeeqser.key)\
                    .filter(Draft.author == self.jeeqser.key)\
                    .filter(Draft.challenge == challenge_key).fetch(1)[0]
            except IndexError:
                draft = Draft(
                    parent=self.jeeqser.key,
                    author=self.jeeqser.key,
                    challenge=challenge_key,
                )
            draft.markdown = solution
            draft.content = markdown.markdown(
                solution, ['codehilite', 'mathjax'])
            draft.put()

        persist_new_draft()

    def update_profile_picture(self):
        profile_picture_url = self.request.get('profile_picture_url')
        if profile_picture_url == self.jeeqser.profile_url:
            return

        self.jeeqser.profile_url = profile_picture_url
        self.jeeqser.put()

    def update_displayname(self):
        displayname = self.request.get('display_name')

        if displayname == self.jeeqser.displayname_persisted:
            # firefox needs some output for a Jquery ajax POST to be a success
            self.response.write('no_operation')
            return

        exists = len(Jeeqser.query(
            Jeeqser.displayname_persisted == displayname).fetch(1)) > 0
        if not exists:
            self.jeeqser.displayname_persisted = displayname
            self.jeeqser.put()
            # firefox needs some output for a Jquery ajax POST to be a success
            self.response.write('success')
            return
        else:
            self.response.write('not_unique')
            return

    @ndb.transactional(xg=True)
    def persist_review(self, feedback,
                       submission_key,
                       jeeqser_challenge_key,
                       jeeqser_key):
        (submission,
         jeeqser_challenge,
         jeeqser) = ndb.get_multi([submission_key,
                                   jeeqser_challenge_key,
                                   jeeqser_key, ])

        RPCHandler.update_graph_for_review(
            submission,
            jeeqser_challenge,
            feedback.review,
            jeeqser)

        ndb.put_multi([
            jeeqser,
            submission,
            submission.author.get(),
            submission.challenge.get(),
            jeeqser_challenge,
            feedback
        ])

        # needs feedback.key!
        Activity(
            parent=jeeqser_key,
            type='reviewing',
            done_by=jeeqser_key,
            done_by_displayname=jeeqser_key.get().displayname,
            done_by_gravatar=jeeqser_key.get().profile_url,
            challenge=submission.challenge,
            challenge_name=submission.challenge.get().name,
            submission=submission.key,
            submission_author=submission.author,
            submission_author_displayname=submission.author.get().displayname,
            submission_author_gravatar=submission.author.get().profile_url,
            feedback=feedback.key
        ).put()

    def verifyReviewerQualified(self, submission):
        """
        Ensure non-admin user is qualified to review
        :param submission: The submission under review.
        """
        if not users.is_current_user_admin():
            reviewer_challenge = get_jeeqser_challenge(
                self.jeeqser.key,
                submission.challenge)
            qualified = reviewer_challenge and\
                reviewer_challenge.status == AttemptStatus.SUCCESS

            if not qualified:
                raise jeeqs_exceptions.ReviewerNotQualified()

    def submit_review(self):

        submission_key = self.getValueInQuery('submission_key')
        review = self.getValueInQuery('review')
        submission = ndb.Key(urlsafe=submission_key).get()
        self.verifyReviewerQualified(submission)

        jeeqser_challenge = get_jeeqser_challenge(
            submission.author,
            submission.challenge,
            create=True,
            submission_key=submission.key)

        feedback = Feedback(
            parent=submission.key,
            attempt=submission.key,
            author=self.jeeqser.key,
            attempt_author=submission.author,
            markdown=self.request.get('response'),
            content=markdown.markdown(
                self.request.get('response'), ['codehilite', 'mathjax']),
            review=review)

        # check flagging limit
        if feedback.review == Review.FLAG:
            flags_left = spam_manager.SpamManager.check_and_update_flag_limit(
                self.jeeqser)
            response = {'flags_left_today': flags_left}
            out_json = json.dumps(response)
            self.response.write(out_json)

            if flags_left == -1:
                return

        self.persist_review(
            feedback,
            submission.key,
            jeeqser_challenge.key,
            self.jeeqser.key)

    @ndb.transactional(xg=True)
    def persist_flag(self, jeeqser_key, feedback_key):

        feedback = feedback_key.get()
        jeeqser = jeeqser_key.get()

        flags_left = spam_manager.SpamManager.check_and_update_flag_limit(
            jeeqser)
        jeeqser.put()
        response = {'flags_left_today': flags_left}

        if flags_left >= 0:
            feedback.flagged_by.append(jeeqser.key)
            feedback.flag_count += 1
            if (feedback.flag_count >=
                spam_manager.SpamManager.FEEDBACK_FLAG_THRESHOLD) or\
                jeeqser.is_moderator or\
                    users.is_current_user_admin():
                feedback.flagged = True
                author = feedback.author.get()
                spam_manager.SpamManager.flag_author(author)
                author.put()
            feedback.put()

        return response

    def flag_feedback(self):
        feedback_key = self.getValueInQuery('feedback_key')
        feedback = ndb.Key(urlsafe=feedback_key).get()

        if self.jeeqser.key not in feedback.flagged_by:
            response = self.persist_flag(self.jeeqser.key, feedback.key)
            out_json = json.dumps(response)
            self.response.write(out_json)

    def took_tour(self):
        jeeqser_key = self.getValueInQuery('jeeqser_key')
        jeeqser = ndb.Key(urlsafe=jeeqser_key).get()
        jeeqser.took_tour = True
        jeeqser.put()

    @ndb.transactional
    def submit_vote(self):
        submission_key = self.getValueInQuery('submission')
        direction = self.getValueInQuery('direction')
        original_vote = self.getValueInQuery('original_vote')
        submission = None
        try:
            submission = ndb.Key(urlsafe=submission_key).get()
        finally:
            if not submission:
                self.error(status_code.StatusCode.forbidden)
                return

        # remove previous state, if any
        try:
            if original_vote == Attempt.IS_UPVOTED:
                submission.votes_total -= 1
                submission.upvoted.remove(self.jeeqser.key)
            elif original_vote == Attempt.IS_DOWNVOTED:
                submission.votes_total += 1
                submission.downvoted.remove(self.jeeqser.key)
        except ValueError:
            logging.error('Could not remove the user with key %s from the list '
                'of voters, data might be inconsistent' % self.jeeqser.key)

        if direction == Attempt.IS_UPVOTED:
            submission.votes_total += 1
            submission.upvoted.append(self.jeeqser.key)
        elif direction == Attempt.IS_DOWNVOTED:
            submission.votes_total -= 1
            submission.downvoted.append(self.jeeqser.key)
        else:
            logging.warn('Unknown vote direction: %s' % direction)

        submission.put()

    @core.authenticate(False)
    def get_challenge_avatars(self):
        logging.debug("get_challenge_avatatars Start")
        challenge = ndb.Key(urlsafe=self.request.get('challenge_key')).get()
        logging.debug("challenge key : %s" % str(challenge.key))
        solver_jc_list = Jeeqser_Challenge\
            .query()\
            .filter(Jeeqser_Challenge.challenge == challenge.key)\
            .filter(Jeeqser_Challenge.status == AttemptStatus.SUCCESS)\
            .order(-Jeeqser_Challenge.status_changed_on)\
            .fetch(20)

        solver_keys = []
        for jc in solver_jc_list:
            logging.debug(
                "appending one more jeeqser's key : %s" % str(jc.jeeqser))
            solver_keys.append(jc.jeeqser)

        solver_jeeqsers = ndb.get_multi(solver_keys)
        vars = {'solver_jeeqsers': solver_jeeqsers}
        template = core.jinja_environment.get_template(
            'challenge_avatars.html')
        rendered = template.render(vars)
        self.response.write(rendered)


def handle_automatic_review(
        attempt_key, challenge_key, jeeqser_challenge_key, program):
    """Handles submission review for automatic review challenges."""
    attempt, challenge, jeeqser_challenge = ndb.get_multi(
        [ndb.Key(urlsafe=attempt_key),
         ndb.Key(urlsafe=challenge_key),
         ndb.Key(urlsafe=jeeqser_challenge_key)])
    review, output = program_tester.run_testcases(
        program,
        challenge)
    robot = core.get_jeeqs_robot()
    feedback = Feedback(
        parent=attempt.key,
        attempt=attempt.key,
        author=robot.key,
        attempt_author=attempt.author,
        markdown=output,
        content=markdown.markdown(output, ['codehilite', 'mathjax']),
        review=review)
    persist_testcase_results(
        attempt.key, jeeqser_challenge.key, feedback, robot.key)


@ndb.transactional(xg=True)
def persist_testcase_results(
        attempt_key, jeeqser_challenge_key, feedback, reviewer_key):
    attempt, jeeqser_challenge, reviewer = ndb.get_multi(
        [attempt_key, jeeqser_challenge_key, reviewer_key])
    RPCHandler.update_graph_for_review(
        attempt,
        jeeqser_challenge,
        feedback.review,
        reviewer)

    feedback.put()
    jeeqser_challenge.put()
    attempt.put()
    attempt.challenge.get().put()
    attempt.author.get().put()
    reviewer.put()
    # attempt.author doesn't need to be persisted,
    # since it will only change when an attempt is flagged.

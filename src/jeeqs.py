#!/usr/bin/python

"""
A program for managing challenges, attempt and solutions.

"""

import os
import sys
import logging

import webapp2
from review_handler import ReviewHandler

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

from google.appengine.api.datastore_errors import Rollback
import json

from models import *
from utils import *
from spam_manager import *
from program_tester import *
from user_handler import UserHandler

from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb

import lib.markdown as markdown

from core import *

## This for enabling ctypes to improve jinja2 error messages, which is unfortunately not working!
## see: http://stackoverflow.com/a/3694434/195579
#if os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'):
#  # Enable ctypes for Jinja debugging
#  import sys
#  from google.appengine.tools.dev_appserver import HardenedModulesHook
#  assert isinstance(sys.meta_path[0], HardenedModulesHook)
#  sys.meta_path[0]._white_list_c_modules += ['_ctypes', 'gestalt']

# Set to True if stack traces should be shown in the browser, etc.
# TODO: should this be changed into an environment variable ?
_DEBUG = True

# Adds icons and background to feedback objects
def prettify_injeeqs(injeeqs):
    for jeeq in injeeqs:
        if jeeq.vote == 'correct':
            jeeq.icon = 'icon-ok'
            jeeq.background = '#EBFFEB'
        elif jeeq.vote == 'incorrect':
            jeeq.icon = 'icon-remove'
            jeeq.background = '#FFE3E3'
        elif jeeq.vote == 'flag':
            jeeq.icon = 'icon-flag'
            jeeq.background = 'lightgrey'

class FrontPageHandler(webapp2.RequestHandler):
    """renders the home.html template
    """

    @authenticate(False)
    def get(self):
        # get available challenges
        
        all_challenges = Challenge.query().fetch(100)
        all_challenges.sort(
          cmp = exercise_cmp,
          key = lambda challenge:challenge.exercise_number_persisted)

        jeeqser_challenges = []
        if self.jeeqser:
          jeeqser_challenges = Jeeqser_Challenge\
              .query()\
              .filter(Jeeqser_Challenge.jeeqser == self.jeeqser.key)\
              .fetch(100)

        active_submissions = {}
        for jc in jeeqser_challenges:
            active_submissions[jc.challenge] = jc

        injeeqs = None

        if self.jeeqser:
            for ch in all_challenges:
                if active_submissions.get(ch.key):
                    jc = active_submissions[ch.key]
                    ch.submitted = True
                    ch.status = jc.status
                    ch.jc = jc

                else:
                    ch.submitted = False

            injeeqs = Feedback\
                            .query()\
                            .filter(Feedback.attempt_author == self.jeeqser.key)\
                            .filter(Feedback.flagged == False)\
                            .order(Feedback.flag_count)\
                            .order(-Feedback.date)\
                            .fetch(10)
            prettify_injeeqs(injeeqs)

        all_activities = Activity.query().order(-Activity.date).fetch(10)

        vars = add_common_vars({
                'challenges': all_challenges,
                'injeeqs': injeeqs,
                'activities' : all_activities,
                'jeeqser': self.jeeqser,
                'login_url': users.create_login_url(self.request.url),
                'logout_url': users.create_logout_url(self.request.url)
        })

        template = jinja_environment.get_template('home.html')
        rendered = template.render(vars)
        self.response.write(rendered)

class AboutHandler(webapp2.RequestHandler):
    """Renders the About page """

    @authenticate(required=False)
    def get(self):
        vars = add_common_vars({
                'jeeqser' : self.jeeqser,
                'gravatar_url' : self.jeeqser.gravatar_url if self.jeeqser else None,
                'login_url': users.create_login_url(self.request.url),
                'logout_url': users.create_logout_url(self.request.url)
        })

        template = jinja_environment.get_template('about.html')
        rendered = template.render(vars)
        self.response.write(rendered)

class ChallengeHandler(webapp2.RequestHandler):
    """renders the solve_a_challenge.html template
    """

    @authenticate(False)
    def get(self):
        # show this user's previous attempts
        attempts = None
        feedbacks = None
        submission = None
        draft = None

        # get the challenge
        ch_key = self.request.get('ch')
        if not ch_key:
            self.error(StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = ndb.Key(urlsafe=ch_key).get()
        finally:
            if not challenge:
                self.error(StatusCode.forbidden)
                return

        if not challenge.content and challenge.markdown:
            challenge.content = markdown.markdown(challenge.markdown, ['codehilite', 'mathjax'])
            challenge.put()

        attempt = None
        attempt_key = self.request.get('att')
        if attempt_key:
            attempt = submission = ndb.Key(urlsafe=attempt_key).get()

        if (self.jeeqser):
            attempts = Attempt.query()\
                .filter(Attempt.author == self.jeeqser.key)\
                .filter(Attempt.challenge == challenge.key)\
                .order(-Attempt.date)\
                .fetch(20)


            if not submission:
                # fetch user's active submission
                submissions = Attempt.query()\
                    .filter(Attempt.author == self.jeeqser.key)\
                    .filter(Attempt.challenge == challenge.key)\
                    .filter(Attempt.active == True)\
                    .order(-Attempt.date)\
                    .fetch(1)

                if (submissions):
                    submission = submissions[0]

                else:
                    submission = None

            if submission:
                feedbacks = Feedback.query()\
                                    .filter(Feedback.attempt == submission.key)\
                                    .filter(Feedback.flagged == False)\
                                    .order(Feedback.flag_count)\
                                    .order(-Feedback.date)\
                                    .fetch(10)

            if feedbacks:
                prettify_injeeqs(feedbacks)

            # Fetch saved draft
            try:
                draft = Draft.query().filter(
                    Draft.author == self.jeeqser.key,
                    Draft.challenge == challenge.key).fetch(1)[0]
            except IndexError:
                draft = None

        vars = add_common_vars({
                'server_software': os.environ['SERVER_SOFTWARE'],
                'python_version': sys.version,
                'jeeqser': self.jeeqser,
                'login_url': users.create_login_url(self.request.url),
                'logout_url': users.create_logout_url(self.request.url),
                'attempts': attempts,
                'challenge' : challenge,
                'challenge_key' : challenge.key,
                'template_code': challenge.template_code,
                'submission' : submission,
                'feedbacks' : feedbacks,
                'draft': draft,
                'attempt': attempt
        })

        template = jinja_environment.get_template('solve_a_challenge.html')
        rendered = template.render(vars)
        self.response.write(rendered)


class ProgramHandler(webapp2.RequestHandler):
    """Evaluates a python program and returns the result.
    """

    def get(self):
        program = self.request.get('program')
        if not program:
            return

        # retrieve the challenge
        challenge_key = self.request.get('challenge_key')
        if not challenge_key:
            self.error(StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = Challenge.get(challenge_key)
        finally:
            if not challenge:
                self.error(StatusCode.forbidden)
                return

        self.response.headers['Content-Type'] = 'text/plain'

        output = {'result' : ''}

        try:
            compile_and_run(program, output)
        except:
            pass
        finally:
            self.response.write(output['result'])


class RPCHandler(webapp2.RequestHandler):
    """Handles RPC calls
    """

    @authenticate(True)
    def post(self):
        method = self.request.get('method')
        if (not method):
            self.error(StatusCode.forbidden)
            return

        if method == 'submit_vote':
            self.submit_vote()
        elif method == 'update_displayname':
            self.update_displayname()
        elif method == 'update_profile_picture':
            self.update_profile_picture()
        elif method == 'submit_solution':
            self.submit_solution()
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
        else:
            self.error(StatusCode.forbidden)
            return

    def get(self):
        method = self.request.get('method')
        logging.debug("dispatching method %s "% method)
        if (not method):
            self.error(StatusCode.forbidden)
            return

        if method == 'get_in_jeeqs':
            self.get_in_jeeqs()
        elif method == 'get_challenge_avatars':
            self.get_challenge_avatars()
        else:
            self.error(StatusCode.forbidden)
            return

    @staticmethod
    def get_vote_numeric_value(vote):
        if vote == 'correct':
            return 2
        elif vote == 'incorrect':
            return 0
        else:
            return 0 # flag

    @staticmethod
    def update_graph_vote_submitted(submission, jeeqser_challenge, vote, voter):
        """
        Updates the model graph based on the vote given by the voter
        """
        submission.users_voted.append(voter.key)
        submission.vote_count += 1
        if submission.vote_count == 1:
            submission.challenge.submissions_without_review -= 1

        submission.vote_sum += float(RPCHandler.get_vote_numeric_value(vote))
        submission.vote_average = float(submission.vote_sum / submission.vote_count)

        # update stats
        voter.reviews_out_num += 1
        submission.author.reviews_in_num +=1

        if vote == 'correct':
            submission.correct_count += 1
            jeeqser_challenge.correct_count = submission.correct_count
        elif vote == 'incorrect':
            submission.incorrect_count += 1
            jeeqser_challenge.incorrect_count = submission.incorrect_count
        elif vote == 'flag':
            submission.flag_count += 1
            jeeqser_challenge.flag_count = submission.flag_count
            if (submission.flag_count > spam_manager.submission_flag_threshold) or voter.is_moderator or users.is_current_user_admin():
                submission.flagged = True
                spam_manager.flag_author(submission.author)
            submission.flagged_by.append(voter.key)

        previous_status = jeeqser_challenge.status

        #update status on submission and jeeqser_challenge
        if submission.correct_count > submission.incorrect_count + submission.flag_count:
            submission.status = jeeqser_challenge.status = 'correct'
        else:
            submission.status = jeeqser_challenge.status = 'incorrect'

        # TODO: This may not scale since challenge's entity group is high traffic - use sharded counters
        if jeeqser_challenge.status != previous_status:
            jeeqser_challenge.status_changed_on = datetime.now()

            if jeeqser_challenge.status == 'correct':
                submission.challenge.num_jeeqsers_solved += 1
                submission.challenge.update_last_solver(submission.author)
                submission.author.correct_submissions_count += 1

            elif jeeqser_challenge.status == 'incorrect':
                if previous_status == 'correct':
                    submission.challenge.num_jeeqsers_solved -= 1
                    submission.author.correct_submissions_count -= 1
                if submission.challenge.last_solver and submission.challenge.last_solver.key == submission.author.key:
                    submission.challenge.update_last_solver(None)

    @authenticate(False)
    def get_in_jeeqs(self):
        submission_key = self.request.get('submission_key')

        submission = None

        try:
            submission = ndb.Key(urlsafe=submission_key).get()
        finally:
            if not submission:
                self.error(StatusCode.forbidden)
                return

        # TODO: We can optimize these kind of calls by never retrieving submission object
        feedbacks = Feedback.query()\
            .filter(Feedback.attempt == submission.key)\
            .filter(Feedback.flagged == False)\
            .order(Feedback.flag_count)\
            .order(-Feedback.date)\
            .fetch(10)

        if feedbacks:
            prettify_injeeqs(feedbacks)

        vars = add_common_vars({
            'feedbacks' : feedbacks,
            'jeeqser': self.jeeqser
        })

        template = jinja_environment.get_template('in_jeeqs_list.html')
        rendered = template.render(vars)
        self.response.write(rendered)


    def submit_challenge_vertical_scroll(self):
        """updates a challenge's source url """
        if not users.is_current_user_admin():
            self.error(StatusCode.unauth)
            return

        new_vertical_scroll = self.request.get('vertical_scroll')
        if not new_vertical_scroll:
            self.error(StatusCode.forbidden)
            return

        # retrieve the challenge
        challenge_key = self.request.get('challenge_key')
        if not challenge_key:
            self.error(StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = Challenge.get(challenge_key);
        finally:
            if not challenge:
                self.error(StatusCode.forbidden)
                return

        challenge.vertical_scroll = float(new_vertical_scroll)
        challenge.put()

    def submit_challenge_source(self):
        """updates a challenge's source """
        if not users.is_current_user_admin():
            self.error(StatusCode.unauth)
            return

        new_source = self.request.get('source')
        if not new_source:
            self.error(StatusCode.forbidden)
            return

        # retrieve the challenge
        challenge_key = self.request.get('challenge_key')
        if not challenge_key:
            self.error(StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = Challenge.get(challenge_key);
        finally:
            if not challenge:
                self.error(StatusCode.forbidden)
                return

        challenge.markdown = new_source
        challenge.content = markdown.markdown(challenge.markdown, ['codehilite', 'mathjax'])
        challenge.put()

    def submit_solution(self):
        """
        Submits a solution
        """
        program = solution = self.request.get('solution')
        if not solution:
            return

        # retrieve the challenge
        challenge_key = self.request.get('challenge_key')
        if not challenge_key:
            self.error(StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = Challenge.get(challenge_key);
        finally:
            if not challenge:
                self.error(StatusCode.forbidden)

        if challenge.automatic_review:
            new_solution = '    :::python' + '\n'
            for line in solution.splitlines(True):
                new_solution += '    ' + line
            solution = new_solution

        jeeqser_challenge = get_JC(self.jeeqser, challenge)

        context = {'jeeqser' : self.jeeqser, 'jeeqser_challenge': jeeqser_challenge}

        def persist_new_submission():

            jeeqser_challenge = context['jeeqser_challenge']
            previous_index = 0

            if len(jeeqser_challenge) == 1:
                jeeqser_challenge = jeeqser_challenge[0]
                jeeqser_challenge.active_attempt.active = False
                jeeqser_challenge.active_attempt.put()
                previous_index = jeeqser_challenge.active_attempt.index

                if jeeqser_challenge.status == 'correct' :
                    if challenge.num_jeeqsers_solved > 0:
                        challenge.num_jeeqsers_solved -=1
                    else:
                        logging.error("Challenge %s can not have negative solvers! " % challenge.key)
            else:
                #create one
                jeeqser_challenge = Jeeqser_Challenge(
                    parent=self.jeeqser,
                    jeeqser = self.jeeqser,
                    challenge = challenge
                )
                challenge.num_jeeqsers_submitted += 1

            if challenge.last_solver and challenge.last_solver.key == self.jeeqser.key:
                challenge.update_last_solver(None)

            challenge.submissions_without_review += 1

            challenge.put()

            attempt = Attempt(
                author=self.jeeqser.key,
                challenge=challenge,
                content=markdown.markdown(solution, ['codehilite', 'mathjax']),
                markdown=solution,
                active=True,
                index=previous_index + 1)

            attempt.put()

            if jeeqser_challenge.status == 'correct':
                self.jeeqser.correct_submissions_count -= 1

            jeeqser_challenge.active_attempt = attempt
            jeeqser_challenge.correct_count = jeeqser_challenge.incorrect_count = jeeqser_challenge.flag_count = 0
            jeeqser_challenge.status = None
            jeeqser_challenge.put()

            self.jeeqser.submissions_num += 1
            self.jeeqser.put()

            # Pass variables up
            context['jeeqser'] = self.jeeqser
            context['attempt'] = attempt
            context['jeeqser_challenge'] = jeeqser_challenge

        xg_on = db.create_transaction_options(xg=True)
        db.run_in_transaction_options(xg_on, persist_new_submission)
        # Receive variables from transaction
        self.jeeqser = context['jeeqser']
        attempt = context['attempt']
        jeeqser_challenge = context['jeeqser_challenge']

        # delete a draft if exists
        try:
            draft = Draft.query(ancestor=self.jeeqser).filter(
                Draft.challenge == ndb.Key.from_old_key((challenge.key))).fetch(1)[0]
            draft.delete()
        except IndexError:
            pass

        # TODO: Do this asynchronously!
        # run the tests and persist the results
        if challenge.automatic_review:
            feedback = run_testcases(program, challenge, attempt, get_jeeqs_robot())
            voter = Jeeqser.get_review_user()

            def persist_testcase_results():
                RPCHandler.update_graph_vote_submitted(attempt, jeeqser_challenge, feedback.vote, voter)

                feedback.put()
                jeeqser_challenge.put()
                attempt.put()
                attempt.challenge.put()
                attempt.author.put()
                voter.put()
                # attempt.author doesn't need to be persisted, since it will only change when an attempt is flagged.

            xg_on = db.create_transaction_options(xg=True)
            db.run_in_transaction_options(xg_on, persist_testcase_results)

        Activity(
            type='submission',
            done_by=self.jeeqser,
            done_by_displayname=self.jeeqser.displayname,
            done_by_gravatar=self.jeeqser.profile_url,
            challenge=challenge,
            challenge_name=challenge.name).put()

    def save_draft_solution(self):
        """
        Submits a solution
        """
        solution = self.request.get('solution')
        if not solution:
            self.error(StatusCode.bad)
            return

        # retrieve the challenge
        challenge_key = self.request.get('challenge_key')
        if not challenge_key:
            self.error(StatusCode.forbidden)
            return

        challenge = None

        try:
            challenge = Challenge.get(challenge_key);
        finally:
            if not challenge:
                self.error(StatusCode.forbidden)

        def persist_new_draft():
            try:
                draft = Draft.query(ancestor=self.jeeqser) \
                    .filter(Draft.author == ndb.Key.from_old_key(self.jeeqser.key)) \
                    .filter(Draft.challenge == ndb.Key.from_old_key(challenge.key)).fetch(1)[0]
            except IndexError:
                draft = Draft(
                    parent=self.jeeqser,
                    author=self.jeeqser,
                    challenge = challenge,
                )

            draft.markdown = solution
            draft.content = markdown.markdown(solution, ['codehilite', 'mathjax'])

            draft.put()

        xg_on = db.create_transaction_options(xg=True)
        db.run_in_transaction_options(xg_on, persist_new_draft)

    def update_profile_picture(self):
        profile_picture_url = self.request.get('profile_picture_url')
        if profile_picture_url == self.jeeqser.profile_url:
            return

        self.jeeqser.profile_url = profile_picture_url
        self.jeeqser.put()

    def update_displayname(self):
        displayname = self.request.get('display_name')

        if displayname == self.jeeqser.displayname_persisted:
            return;

        exists = len(Jeeqser.all().filter('displayname_persisted = ', displayname).fetch(1)) > 0
        if not exists:
            self.jeeqser.displayname = displayname
            self.jeeqser.put()
        else:
            self.response.write('not_unique')
            return

    def submit_vote(self):

        submission_key = self.request.get('submission_key')
        vote = self.request.get('vote')


        submission = None

        try:
            submission = ndb.Key(urlsafe=submission_key).get()
        finally:
            if not submission:
                self.error(StatusCode.forbidden)
                return
        
        #Ensure non-admin user is qualified to vote
        if not users.is_current_user_admin():
            voter_challenge = get_JC(self.jeeqser, submission.challenge)
            qualified = voter_challenge and voter_challenge[0].status == 'correct'
            
            if not qualified:
                self.error(StatusCode.forbidden)
                return
        
        jeeqser_challenge = get_JC(submission.author,submission.challenge)

        if len(jeeqser_challenge) == 0:
            # should never happen but let's guard against it!
            logging.error("Jeeqser_Challenge not available! for jeeqser : " + submission.author.user.email() + " and challenge : " + submission.challenge.name)
            jeeqser_challenge = Jeeqser_Challenge(
                parent = submission.author,
                jeeqser = submission.author,
                challenge = submission.challenge,
                active_attempt = submission)
            jeeqser_challenge.put()
        else:
            jeeqser_challenge = jeeqser_challenge[0]

        feedback = Feedback(
            parent=submission.key,
            attempt=submission,
            author=self.jeeqser,
            attempt_author=submission.author,
            markdown=self.request.get('response'),
            content=markdown.markdown(self.request.get('response'), ['codehilite', 'mathjax']),
            vote=vote)

        def persist_vote(submission_key, jeeqser_challenge_key, jeeqser_key):
            # get all the objects that will be updated
            submission = ndb.Key(urlsafe=submission_key).get()
            jeeqser_challenge = ndb.Key(urlsafe=jeeqser_challenge_key).get()
            jeeqser = ndb.Key(urlsafe=jeeqser_key).get()
            submission.author = submission.author.get()

            # check flagging limit
            if vote == 'flag':
                flags_left = spam_manager.check_and_update_flag_limit(jeeqser)
                response = {'flags_left_today':flags_left}
                out_json = json.dumps(response)
                self.response.write(out_json)

                if flags_left == -1:
                    raise Rollback()

            RPCHandler.update_graph_vote_submitted(submission, jeeqser_challenge, vote, jeeqser)

            jeeqser_challenge.put()
            submission.put()
            submission.challenge.put()
            jeeqser.put()
            submission.author.put()
            feedback.put()

        xg_on = db.create_transaction_options(xg=True)
        db.run_in_transaction_options(
            xg_on,
            persist_vote,
            submission.key,
            jeeqser_challenge.key,
            self.jeeqser.key)

        Activity(
            type='voting',
            done_by = self.jeeqser,
            done_by_displayname=self.jeeqser.displayname,
            done_by_gravatar = self.jeeqser.profile_url,
            challenge=submission.challenge,
            challenge_name=submission.challenge.name,
            submission=submission,
            submission_author=submission.author,
            submission_author_displayname=submission.author.displayname,
            submission_author_gravatar = submission.author.profile_url,
            feedback=feedback
        ).put()


    def flag_feedback(self):
        feedback_key = self.request.get('feedback_key')
        feedback = Feedback.get(feedback_key)

        if self.jeeqser.key not in feedback.flagged_by:
            def persist_flag(jeeqser_key):

                feedback = Feedback.get(feedback_key)
                jeeqser = Jeeqser.get(jeeqser_key)

                flags_left = spam_manager.check_and_update_flag_limit(jeeqser)
                jeeqser.put()
                response = {'flags_left_today':flags_left}

                if flags_left >= 0:
                    feedback.flagged_by.append(jeeqser.key)
                    feedback.flag_count += 1
                    if (feedback.flag_count >= spam_manager.feedback_flag_threshold) or jeeqser.is_moderator or users.is_current_user_admin():
                        feedback.flagged = True
                        spam_manager.flag_author(feedback.author)
                        feedback.author.put()
                    feedback.put()

                return response

            xg_on = db.create_transaction_options(xg=True)
            response = db.run_in_transaction_options(xg_on, persist_flag, self.jeeqser.key)


            out_json = json.dumps(response)
            self.response.write(out_json)

    def took_tour(self):
        jeeqser_key = self.request.get('jeeqser_key')
        jeeqser = Jeeqser.get(jeeqser_key)

        jeeqser.took_tour = True
        jeeqser.put()

    @authenticate(False)
    def get_challenge_avatars(self):
        logging.debug("here at get_challenge_avatatars")
        challenge = ndb.Key(urlsafe=self.request.get('challenge_key')).get()
        logging.debug("challenge key : %s" % str(challenge.key))
        solver_jc_list = Jeeqser_Challenge\
                        .query()\
                        .filter(Jeeqser_Challenge.challenge == challenge.key)\
                        .filter(Jeeqser_Challenge.status == 'correct')\
                        .order(-Jeeqser_Challenge.status_changed_on)\
                        .fetch(20)

        solver_keys = []
        for jc in solver_jc_list:
            logging.debug("appending one more jeeqser's key : %s" % str(jc.jeeqser))
            solver_keys.append(jc.jeeqser)

        solver_jeeqsers = ndb.get_multi(solver_keys)
        vars = {'solver_jeeqsers' : solver_jeeqsers}
        template = jinja_environment.get_template('challenge_avatars.html')
        rendered = template.render(vars)
        self.response.write(rendered)

def main():
    application = webapp2.WSGIApplication(
        [('/', FrontPageHandler),
            ('/challenge/', ChallengeHandler),
            ('/challenge/shell.runProgram', ProgramHandler),
            ('/review/', ReviewHandler),
            ('/rpc', RPCHandler),
            ('/user/', UserHandler),
            ('/about/', AboutHandler)])
    run_wsgi_app(application)


if __name__ == '__main__':
    main()

import os
import sys
from core import *
from status_code import StatusCode
from google.appengine.ext import ndb
import jeeqs_request_handler

SUBMISSIONS_PER_PAGE = 5


class ReviewHandler(jeeqs_request_handler.JeeqsRequestHandler):
    """renders the review template
    """

    @authenticate(False)
    def get(self):

        if not self.jeeqser:
            self.response.write('<div style="color: grey">You need to be ' +
                                'logged in to see other submissions</div>')
            return

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

        next_cursor = None
        previous_cursor = None
        cursor = self.request.get('cursor') if self.request.get('cursor') \
            else None

        # determine if the user is qualified to review
        # this challenge's submissions
        if not users.is_current_user_admin():
            self_challenge = get_jeeqser_challenge(self.jeeqser.key,
                                                   challenge.key)
            review_qualified = self_challenge and \
                self_challenge.status == AttemptStatus.SUCCESS
        else:
            review_qualified = True

        # contains latest reviews from current user
        # for submissions on this page
        own_reviews = {}

        if review_qualified or challenge.public_submissions:
            # Retrieve other users' submissions
            submissions_query = Attempt.query()\
                .filter(Attempt.challenge == challenge.key)\
                .filter(Attempt.active == True)\
                .filter(Attempt.flagged == False)\
                .order(Attempt.vote_count)

            if cursor and cursor != "None":
                qo = ndb.QueryOptions(start_cursor=ndb.Cursor(urlsafe=cursor))
            else:
                qo = ndb.QueryOptions()

            submissions, next_cursor, more = submissions_query.fetch_page(
                SUBMISSIONS_PER_PAGE, options=qo)

            if next_cursor:
                next_cursor = next_cursor.urlsafe()
            previous_cursor = cursor

            # TODO: replace this iteration with a data oriented approach
            submissions[:] = [submission for submission in submissions if
                              not (submission.author == self.jeeqser.key)]
            # or self.jeeqser.key() in submission.users_voted)]

            for submission in submissions:
                review = Feedback.query().\
                    filter(Feedback.attempt == submission.key).\
                    filter(Feedback.author == self.jeeqser.key).\
                    order(-Feedback.date).fetch(1)
                if len(review) > 0:
                    own_reviews[submission.key.urlsafe()] = review[0]
        else:
            submissions, next_cursor, more = [], 'None', False

        vars = add_common_vars({
            'server_software': os.environ['SERVER_SOFTWARE'],
            'python_version': sys.version,
            'jeeqser': self.jeeqser,
            'login_url': users.create_login_url(self.request.url),
            'logout_url': users.create_logout_url(self.request.url),
            'challenge': challenge,
            'submissions': submissions,
            'review_qualified': review_qualified,
            'next_cursor': next_cursor,
            'previous_cursor': previous_cursor,
            'more': more,
            'own_reviews': own_reviews
        })

        template = jinja_environment.get_template('review_a_challenge.html')
        rendered = template.render(vars)
        self.response.write(rendered)

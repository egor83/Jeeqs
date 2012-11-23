import os
import sys
import webapp2
from core import *
from utils import StatusCode
from google.appengine.ext import ndb

class ReviewHandler(webapp2.RequestHandler):
    """renders the review template
    """

    @authenticate(False)
    def get(self):

        if not self.jeeqser:
            self.response.write('<div style="color: grey">You need to be logged in to see other submissions</div>')
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
        cursor = self.request.get('cursor') if self.request.get('cursor') else None

        # determine if the user is qualified to review this challenge's submissions
        if not users.is_current_user_admin():
            self_challenge = get_JC(self.jeeqser,challenge)
            review_qualified = self_challenge and self_challenge[0].status == 'correct'
        else:
            review_qualified = True

        if review_qualified or challenge.public_submissions:
            # Retrieve other users' submissions
            submissions_query = Attempt.query()\
                .filter(Attempt.challenge == challenge.key)\
                .filter(Attempt.active == True)\
                .filter(Attempt.flagged == False)\
                .order(Attempt.vote_count)

            if cursor and cursor != "None":
                submissions_query.with_cursor(cursor)

            submissions = submissions_query.fetch(5)

            previous_cursor = cursor
            next_cursor = submissions_query.cursor()

            # TODO: replace this iteration with a data oriented approach
            submissions[:] = [submission for submission in submissions if not (submission.author.key() == self.jeeqser.key())] # or self.jeeqser.key() in submission.users_voted)]
        else:
             submissions = []

        vars = add_common_vars({
                'server_software': os.environ['SERVER_SOFTWARE'],
                'python_version': sys.version,
                'jeeqser': self.jeeqser,
                'login_url': users.create_login_url(self.request.url),
                'logout_url': users.create_logout_url(self.request.url),
                'challenge' : challenge,
                'challenge' : challenge,
                'submissions' : submissions,
                'review_qualified' : review_qualified,
                'next_cursor': next_cursor,
                'previous_cursor' : previous_cursor,
        })

        template = jinja_environment.get_template('review_a_challenge.html')
        rendered = template.render(vars)
        self.response.write(rendered)
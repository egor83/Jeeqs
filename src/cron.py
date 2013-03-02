import logging
import webapp2

from google.appengine.ext.webapp.util import run_wsgi_app

from models import *
from status_code import exercise_cmp


class SanityCheck(webapp2.RequestHandler):
    def get(self):
        """Check if  parameter values are consistent.

        Some parameters (for a challenge - # of jeeqsers who submitted
        the solution, # of jeeqsers who solved it, # of submission that don't
        have a review yet) can be calculated in several different ways.

        This method checks their value, if different ways give inconsistent
        results - print an error message to the logs and fix the discrepancy.

        """

        res = []

        all_challenges = Challenge.query().fetch()
        all_challenges.sort(
            cmp=exercise_cmp,
            key=lambda challenge: challenge.exercise_number_persisted)
        for ch in all_challenges:
            num_solved = Jeeqser_Challenge.query()\
                .filter(Jeeqser_Challenge.challenge == ch.key)\
                .filter(Jeeqser_Challenge.status == AttemptStatus.SUCCESS)\
                .count()

            num_submitted = Jeeqser_Challenge.query()\
                .filter(Jeeqser_Challenge.challenge == ch.key)\
                .count()

            num_without_review = Attempt.query().\
                filter(Attempt.challenge == ch.key).\
                filter(Attempt.active == True).\
                filter(Attempt.vote_count == 0).\
                count()

            if (num_submitted != ch.num_jeeqsers_submitted or
                    num_solved != ch.num_jeeqsers_solved or
                    num_without_review != ch.submissions_without_review):
                ch_data = '%-20s: submitted %s/%s, solved %s/%s, ' \
                    'no review: %s/%s' % (ch.name[:20], num_submitted,
                    ch.num_jeeqsers_submitted, num_solved,
                    ch.num_jeeqsers_solved, num_without_review,
                    ch.submissions_without_review)
#                print ch_data

                logging.error('A discrepancy in challenge parameters has been '
                              'found:')
                logging.error(ch_data)
                res.append(ch_data)

                ch.num_jeeqsers_submitted = num_submitted
                ch.num_jeeqsers_solved = num_solved
                ch.submissions_without_review = num_without_review
                ch.put()

        self.response.write('<br />'.join(res))


def main():
#    logging.getLogger().setLevel(logging.DEBUG)
    application = webapp2.WSGIApplication(
        [('/cron/sanity_check/', SanityCheck),])
    run_wsgi_app(application)


if __name__ == '__main__':
    main()

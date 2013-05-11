"""Script used in remote API to refactor votes:

change all vote-related entites to review-related ones.

"""


from google.appengine.ext import ndb
from models import *

# TODO bulk requests/updates

attempts = Attempt.query().fetch()

for att in attempts:
    att.users_reviewed = att.users_voted
    att.users_voted = att.review_count
    att.vote_sum = att.feedback_score_sum
    att.vote_average = att.feedback_score_average

ndb.put_multi(attempts)

feedbacks = Feedback.query().fetch()

for fb in feedbacks:
    fb.review = fb.vote

ndb.put_multi(feedbacks)

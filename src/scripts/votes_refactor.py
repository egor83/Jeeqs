"""Script used in remote API to refactor votes:

change all vote-related entites to review-related ones.

"""


############### Copy new fields' values from existing ones ###############

from google.appengine.ext import ndb
from models import *

attempts = Attempt.query().fetch()

for att in attempts:
    att.users_reviewed = att.users_voted
    att.review_count = att.vote_count
    att.feedback_score_sum = att.vote_sum
    att.feedback_score_average = att.vote_average

ndb.put_multi(attempts)

feedbacks = Feedback.query().fetch()

for fb in feedbacks:
    if fb.vote == u'':
        fb.review = Review.CORRECT
    else:
        fb.review = fb.vote

ndb.put_multi(feedbacks)

############### Migrate existing Activity entities ###############

from google.appengine.ext import ndb
from models import *

acts = Activity.query().filter(Activity.type=='voting').fetch()

for act in acts:
    act.type = 'reviewing'

ndb.put_multi(acts)

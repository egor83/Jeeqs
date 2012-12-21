"""
A class for fighting spam.

"""

from datetime import timedelta
from datetime import datetime
from google.appengine.api import users


class FlaggingLimitReachedError(Exception):
  """
  Thrown if the user has already flagged more than limit.
  """
  pass


class SpamManager:
  # flag threshold for deleting a submission
  SUBMISSION_FLAG_THRESHOLD = 3

  # flag threshold for deleting a feedback
  FEEDBACK_FLAG_THRESHOLD = 3

  # if the author has this many flagged content, he/she will be suspended for one day per violation.
  AUTHOR_SUSPENSION_THRESHOLD = 3

  # number of flagging actions a user can perform in a single day
  FLAGGING_LIMIT_PER_DAY = 5


  @classmethod
  def flag_author(cls, jeeqser):
    """
    This is invoked when an author's submission or feedback is flagged by enough people.
    """
    jeeqser.total_flag_count += 1
    jeeqser.unaccounted_flag_count += 1
    if jeeqser.unaccounted_flag_count >= SpamManager.AUTHOR_SUSPENSION_THRESHOLD:
      jeeqser.unaccounted_flag_count = 0
      oneday = timedelta(days=1)
      if (jeeqser.suspended_until):
        jeeqser.suspended_until = jeeqser.suspended_until + oneday
      else:
        jeeqser.suspended_until = datetime.now() + oneday

  @classmethod
  def check_and_update_flag_limit(cls, jeeqser):
    """
    Checks whether jeeqser is over-limit for flagging and throws FlaggingLimitReachedError if so. If not, increase a counter.
    """

    if users.is_current_user_admin():
      return 1000

    now = datetime.now()
    if not jeeqser.last_flagged_on or jeeqser.last_flagged_on.date() < now.date():
      jeeqser.last_flagged_on = now
      jeeqser.num_flagged_today = 1
      return SpamManager.FLAGGING_LIMIT_PER_DAY - 1
    elif jeeqser.num_flagged_today >= SpamManager.FLAGGING_LIMIT_PER_DAY:
      return -1
    else:
      jeeqser.last_flagged_on = now
      jeeqser.num_flagged_today = jeeqser.num_flagged_today + 1
      return SpamManager.FLAGGING_LIMIT_PER_DAY - jeeqser.num_flagged_today

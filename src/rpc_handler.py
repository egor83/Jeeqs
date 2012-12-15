from models import * 
import core
import utils
import logging
import webapp2
import json
import spam_manager
import program_tester
import datetime
import lib.markdown as markdown
from google.appengine.api import users
from google.appengine.ext import deferred
import jeeqs_request_handler
import jeeqs_exceptions

class RPCHandler(jeeqs_request_handler.JeeqsRequestHandler):
  """Handles RPC calls
  """

  @core.authenticate(True)
  def post(self):
    method = self.request.get('method')
    if (not method):
      self.error(utils.StatusCode.forbidden)
      return

    if method == 'submitVote':
      self.submitVote()
    elif method == 'update_displayname':
      self.update_displayname()
    elif method == 'update_profile_picture':
      self.update_profile_picture()
    elif method == 'submitAttempt':
      self.submitAttempt()
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
      self.error(utils.StatusCode.forbidden)
      return

  def get(self):
    method = self.request.get('method')
    logging.debug("dispatching method %s "% method)
    if (not method):
      self.error(utils.StatusCode.forbidden)
      return

    if method == 'get_in_jeeqs':
      self.get_in_jeeqs()
    elif method == 'get_challenge_avatars':
      self.get_challenge_avatars()
    else:
      self.error(utils.StatusCode.forbidden)
      return

  @staticmethod
  def get_vote_numeric_value(vote):
    if vote == Vote.CORRECT:
      return 2
    elif vote == Vote.INCORRECT:
      return 0
    else:
      return 0 # flag

  @staticmethod
  def updateGraphVoteSubmitted(submission, jeeqser_challenge, vote, voter):
    """
    Updates the model graph based on the vote given by the voter
    """
    # TODO: refactor to simpler and more modularized logic
    submission.users_voted.append(voter.key)
    submission.vote_count += 1
    if submission.vote_count == 1:
      submission.challenge.get().submissions_without_review -= 1

    submission.vote_sum += float(RPCHandler.get_vote_numeric_value(vote))
    submission.vote_average = float(submission.vote_sum / submission.vote_count)

    # update stats
    voter.reviews_out_num += 1
    submission.author.get().reviews_in_num +=1

    if vote == Vote.CORRECT:
      submission.correct_count += 1
      jeeqser_challenge.correct_count = submission.correct_count
    elif vote == Vote.INCORRECT:
      submission.incorrect_count += 1
      jeeqser_challenge.incorrect_count = submission.incorrect_count
    elif vote == Vote.FLAG:
      submission.flag_count += 1
      jeeqser_challenge.flag_count = submission.flag_count
      if (submission.flag_count > spam_manager.submission_flag_threshold) or voter.is_moderator or users.is_current_user_admin():
        submission.flagged = True
        spam_manager.flag_author(submission.author.get())
      submission.flagged_by.append(voter.key)

    previous_status = jeeqser_challenge.status

    #update status on submission and jeeqser_challenge
    if submission.correct_count > submission.incorrect_count + submission.flag_count:
      submission.status = jeeqser_challenge.status = AttemptStatus.SUCCESS
    else:
      submission.status = jeeqser_challenge.status = AttemptStatus.FAIL

    if jeeqser_challenge.status != previous_status:
      jeeqser_challenge.status_changed_on = datetime.datetime.now()

      if jeeqser_challenge.status == AttemptStatus.SUCCESS:
        # TODO: This may not scale since challenge's entity group is high traffic - use sharded counters
        submission.challenge.get().num_jeeqsers_solved += 1
        submission.challenge.get().update_last_solver(submission.author.get())
        submission.author.get().correct_submissions_count += 1

      elif jeeqser_challenge.status == AttemptStatus.FAIL:
        if previous_status == AttemptStatus.SUCCESS:
          submission.challenge.get().num_jeeqsers_solved -= 1
          submission.author.get().correct_submissions_count -= 1
        if submission.challenge.get().last_solver and submission.challenge.get().last_solver == submission.author:
          submission.challenge.get().update_last_solver(None)

  @core.authenticate(False)
  def get_in_jeeqs(self):
    submission_key = self.request.get('submission_key')

    submission = None

    try:
      submission = ndb.Key(urlsafe=submission_key).get()
    finally:
      if not submission:
        self.error(utils.StatusCode.forbidden)
        return

    # TODO: We can optimize these kind of calls by never retrieving submission object
    feedbacks = Feedback.query()\
    .filter(Feedback.attempt == submission.key)\
    .filter(Feedback.flagged == False)\
    .order(Feedback.flag_count)\
    .order(-Feedback.date)\
    .fetch(10)

    if feedbacks:
      core.prettify_injeeqs(feedbacks)

    vars = core.add_common_vars({
      'feedbacks' : feedbacks,
      'jeeqser': self.jeeqser
    })

    template = core.jinja_environment.get_template('in_jeeqs_list.html')
    rendered = template.render(vars)
    self.response.write(rendered)


  def submit_challenge_vertical_scroll(self):
    """updates a challenge's source url """
    if not users.is_current_user_admin():
      self.error(utils.StatusCode.unauth)
      return

    new_vertical_scroll = self.request.get('vertical_scroll')
    if not new_vertical_scroll:
      self.error(utils.StatusCode.forbidden)
      return

    # retrieve the challenge
    challenge_key = self.request.get('challenge_key')
    if not challenge_key:
      self.error(utils.StatusCode.forbidden)
      return

    challenge = None

    try:
      challenge = Challenge.get(challenge_key);
    finally:
      if not challenge:
        self.error(utils.StatusCode.forbidden)
        return

    challenge.vertical_scroll = float(new_vertical_scroll)
    challenge.put()

  def submit_challenge_source(self):
    """updates a challenge's source """
    if not users.is_current_user_admin():
      self.error(utils.StatusCode.unauth)
      return

    new_source = self.request.get('source')
    if not new_source:
      self.error(utils.StatusCode.forbidden)
      return

    # retrieve the challenge
    challenge_key = self.request.get('challenge_key')
    if not challenge_key:
      self.error(utils.StatusCode.forbidden)
      return

    challenge = None

    try:
      challenge = Challenge.get(challenge_key);
    finally:
      if not challenge:
        self.error(utils.StatusCode.forbidden)
        return

    challenge.markdown = new_source
    challenge.content = markdown.markdown(challenge.markdown, ['codehilite', 'mathjax'])
    challenge.put()

  def appendLanguagePrefixForAutomaticReview(self, challenge, solution):
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
    self.jeeqser, challenge = ndb.get_multi([self.jeeqser.key, challenge_key])

    jeeqser_challenge = getJeeqserChallenge(self.jeeqser.key, challenge_key)
    previous_index = 0
    if jeeqser_challenge:
      previous_index = jeeqser_challenge.active_attempt.get().index
      jeeqser_challenge.active_attempt.get().active = False
      jeeqser_challenge.active_attempt.get().put()
      if jeeqser_challenge.status == AttemptStatus.SUCCESS:
        challenge.num_jeeqsers_solved -=1
    else:
      jeeqser_challenge = Jeeqser_Challenge(
        parent=self.jeeqser.key,
        jeeqser = self.jeeqser.key,
        challenge = challenge_key
      )
      challenge.num_jeeqsers_submitted += 1
    if challenge.last_solver and challenge.last_solver.key == self.jeeqser.key:
      challenge.update_last_solver(None)
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
    jeeqser_challenge.correct_count = jeeqser_challenge.incorrect_count = jeeqser_challenge.flag_count = 0
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

  @ndb.transactional(xg=True)
  def persist_testcase_results(
      attempt_key, jeeqser_challenge_key, feedback, voter_key):
    attempt, jeeqser_challenge, voter = ndb.get_multi(
        [attempt_key, jeeqser_challenge_key, voter_key])
    RPCHandler.updateGraphVoteSubmitted(
      attempt,
      jeeqser_challenge,
      feedback.vote,
      voter)

    feedback.put()
    jeeqser_challenge.put()
    attempt.put()
    attempt.challenge.get().put()
    attempt.author.get().put()
    voter.put()
    # attempt.author doesn't need to be persisted,
    # since it will only change when an attempt is flagged.

  def handleAutomaticReview(
      attempt_key, challenge_key, jeeqser_challenge_key, program):
    """Handles submission review for automatic review challenges."""
    attempt, challenge, jeeqser_challenge = ndb.get_multi(
        [attempt_key, challenge_key, jeeqser_challenge_key])
    feedback = program_tester.run_testcases(
      program,
      challenge,
      attempt,
      core.get_jeeqs_robot())
    voter = Jeeqser.get_automatic_review_user()
    RPCHandler.persist_testcase_results(attempt.key, jeeqser_challenge.key, feedback, voter.key)

  def submitAttempt(self):
    """
    Submits a solution
    """
    program = solution = self.getValueInQuery('solution')
    challenge_key = ndb.Key(urlsafe=self.getValueInQuery('challenge_key'))
    # no need to test if challenge exists, since if it doesn't we will throw
    # here and the upper stream will convert the exception to user output
    challenge = challenge_key.get()
    solution = self.appendLanguagePrefixForAutomaticReview(challenge, solution)
    self.jeeqser, attempt, jeeqser_challenge = self.persistAttempt(challenge_key, solution)

    # delete a draft if exists
    draft = Draft.query(ancestor=self.jeeqser.key).filter(
        Draft.challenge == challenge_key).fetch(1)
    if draft and len(draft) > 0:
      draft[0].delete()

    if challenge.automatic_review:
      deferred.defer(
          RPCHandler.handleAutomaticReview,
          attempt.key.urlsafe(),
          challenge.key.urlsafe(),
          jeeqser_challenge.key.urlsafe(),
          program)

  def save_draft_solution(self):
    """
    Submits a solution
    """
    solution = self.request.get('solution')
    if not solution:
      self.error(utils.StatusCode.bad)
      return

    # retrieve the challenge
    challenge_key = self.request.get('challenge_key')
    if not challenge_key:
      self.error(utils.StatusCode.forbidden)
      return

    challenge = None

    try:
      challenge = Challenge.get(challenge_key);
    finally:
      if not challenge:
        self.error(utils.StatusCode.forbidden)

    def persist_new_draft():
      try:
        draft = Draft.query(ancestor=self.jeeqser)\
                .filter(Draft.author == ndb.Key.from_old_key(self.jeeqser.key))\
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

  @ndb.transactional(xg=True)
  def persistVote(self, feedback, submission_key, jeeqser_challenge_key, jeeqser_key):
    submission, jeeqser_challenge, jeeqser = ndb.get_multi([
      submission_key,
      jeeqser_challenge_key,
      jeeqser_key,
    ])

    RPCHandler.updateGraphVoteSubmitted(submission, jeeqser_challenge, feedback.vote, jeeqser)

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
      type='voting',
      done_by = jeeqser_key,
      done_by_displayname=jeeqser_key.get().displayname,
      done_by_gravatar = jeeqser_key.get().profile_url,
      challenge=submission.challenge,
      challenge_name=submission.challenge.get().name,
      submission=submission.key,
      submission_author=submission.author,
      submission_author_displayname=submission.author.get().displayname,
      submission_author_gravatar = submission.author.get().profile_url,
      feedback=feedback.key
    ).put()

  def verifyReviewerQualified(self, submission):
    """
    Ensure non-admin user is qualified to vote
    :param submission: The submission under review.
    """
    if not users.is_current_user_admin():
      voter_challenge = getJeeqserChallenge(
          self.jeeqser.key,
          submission.challenge)
      qualified = voter_challenge and \
                  voter_challenge.status == AttemptStatus.SUCCESS

      if not qualified:
        raise jeeqs_exceptions.ReviewerNotQualified()

  def submitVote(self):

    submission_key = self.getValueInQuery('submission_key')
    vote = self.getValueInQuery('vote')
    submission = ndb.Key(urlsafe=submission_key).get()
    self.verifyReviewerQualified(submission)

    jeeqser_challenge = getJeeqserChallenge(
        submission.author,
        submission.challenge,
        create=True,
        submission_key=submission_key)

    feedback = Feedback(
      parent=submission.key,
      attempt=submission.key,
      author=self.jeeqser.key,
      attempt_author=submission.author,
      markdown=self.request.get('response'),
      content=markdown.markdown(self.request.get('response'), ['codehilite', 'mathjax']),
      vote=vote)

    # check flagging limit
    if feedback.vote == 'flag':
      flags_left = spam_manager.check_and_update_flag_limit(self.jeeqser)
      response = {'flags_left_today':flags_left}
      out_json = json.dumps(response)
      self.response.write(out_json)

      if flags_left == -1:
        return

    self.persistVote(
        feedback,
        submission.key,
        jeeqser_challenge.key,
        self.jeeqser.key)

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
      logging.debug("appending one more jeeqser's key : %s" % str(jc.jeeqser))
      solver_keys.append(jc.jeeqser)

    solver_jeeqsers = ndb.get_multi(solver_keys)
    vars = {'solver_jeeqsers' : solver_jeeqsers}
    template = core.jinja_environment.get_template('challenge_avatars.html')
    rendered = template.render(vars)
    self.response.write(rendered)


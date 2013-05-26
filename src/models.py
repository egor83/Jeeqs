#!/usr/bin/python

"""
Model for challenges and solutions.

In order to backup the local data store, first create DataStore stats using
the local Admin console and then run the following command:

These commands are working on Python 2.5.4 as of now. There are known issues
with default installations of python on MacOS and serialization of floats.

Download from GAE datastore into a local file
appcfg.py download_data --url=http://jeeqsy.appspot.com/_ah/remote_api --filename=[db_backup_2012_May_19th] --application=s~jeeqsy

Upload from a file into production: (if you increase num_threads, you might
run into pipe issues with local dev server)
appcfg.py upload_data --url=http://localhost:8080/_ah/remote_api --filename=[db_backup_2012_May_19th] --num_threads=1

In order to use the remote api use the following statement:
python /Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine/remote_api_shell.py -s localhost:8080/_ah/remote_api

For production:
python2.7 /Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine/remote_api_shell.py -s oauth-test.jeeqsy.appspot.com

Initializing the submissions_without_review for challenges:

from models import *
all_challenges = Challenge.all().fetch(1000)

for ch in all_challenges:
   unreviewed = 0
   atts = Attempt.all().filter('challenge = ', ch).filter('active = ', True).fetch(1000)
   for att in atts:
     if att.review_count == 0:
       unreviewed += 1
   ch.submissions_without_review = unreviewed
   ch.put()

For production:

s~jeeqsy> sys.path.append('/Users/nomadali/jeeqs/Jeeqs/src')
s~jeeqsy> from models import *
s~jeeqsy> all_ch = Challenge.all().fetch(1000)
s~jeeqsy> for ch in all_ch:
...   unreviewed = 0
...   for att in ch.attempt_set:
...     if att.active and att.review_count == 0:
...        unreviewed +=1
...   ch.submissions_without_review = unreviewed
...   ch.put()
...

How to access remote api:
python /Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine/remote_api_shell.py -s jeeqsy.appspot.com
Then add models.py base directory to sys.path
(actually if you call remote API from <JEEQS_DIR>/src (the directory where
models.py is located), you will be able to import models and other modules
directly without altering sys.path)

"""

from google.appengine.ext import ndb
import logging
from gravatar import get_profile_url

# Maximum number of entities to fetch
MAX_FETCH = 1000


class AttemptStatus():
    """
    The status of an attempt
    """
    SUCCESS = 'correct'
    FAIL = 'incorrect'


class Jeeqser(ndb.Model):
    """ A Jeeqs User """
    user = ndb.UserProperty()
    displayname_persisted = ndb.StringProperty()
    reviews_out_num = ndb.IntegerProperty(default=0)
    reviews_in_num = ndb.IntegerProperty(default=0)
    submissions_num = ndb.IntegerProperty(default=0)
    correct_submissions_count_persisted = ndb.IntegerProperty()
    gravatar_url_persisted = ndb.StringProperty()
    gplus_picture_url = ndb.StringProperty()
    profile_url_persisted = ndb.StringProperty()
    is_moderator = ndb.BooleanProperty()
    took_tour = ndb.BooleanProperty()
    suspended_until = ndb.DateTimeProperty()
    unaccounted_flag_count = ndb.IntegerProperty(default=0)
    # Total number of posts by this user that are flagged
    total_flag_count = ndb.IntegerProperty(default=0)

    # Flag limits
    last_flagged_on = ndb.DateTimeProperty()
    # Number of posts this jeeqser has flagged today
    num_flagged_today = ndb.IntegerProperty()

    @property
    def correct_submissions_count(self):
        if not self.correct_submissions_count_persisted:
            # calculate submissions that are correct by this Jeqeqser
            correct_count = Jeeqser_Challenge.query(ancestor=self.key)\
                .filter(Jeeqser_Challenge.jeeqser == self.key)\
                .filter(Jeeqser_Challenge.status == AttemptStatus.SUCCESS)\
                .count()
            self.correct_submissions_count_persisted = correct_count
            self.put()
            return self.correct_submissions_count_persisted
        else:
            return self.correct_submissions_count_persisted

    @correct_submissions_count.setter
    def correct_submissions_count(self, value):
        self.correct_submissions_count_persisted = value

    @property
    def profile_url(self):
        if self.profile_url_persisted:
            return self.profile_url_persisted
        else:
            self.profile_url_persisted = self.gravatar_url
            self.put()
            return self.profile_url_persisted

    @profile_url.setter
    def profile_url(self, value):
        self.profile_url_persisted = value

    def get_displayname(self):
        return self.displayname_persisted

    def set_displayname(self, value):
        self.displayname_persisted = value

    # Proxy for persisted displayname # TODO: upgrade to property decorator in
    # python 2.7
    displayname = property(get_displayname, set_displayname, "Display name")

    def get_gravatar_url(self):
        if self.gravatar_url_persisted is None:
            self.gravatar_url_persisted = get_profile_url(self.user.email())
            self.put()
        return self.gravatar_url_persisted

    def set_gravatar_url(self, value):
        self.gravatar_url_persisted = value

    gravatar_url = property(get_gravatar_url, set_gravatar_url, "Gravatar URL")


class University(ndb.Model):
    name = ndb.StringProperty()
    fullname = ndb.StringProperty()


class Program(ndb.Model):
    name = ndb.StringProperty()
    fullname = ndb.StringProperty()
    university = ndb.KeyProperty(kind=University)


class Course(ndb.Model):
    name = ndb.StringProperty()
    code = ndb.StringProperty()
    description = ndb.TextProperty()
    level = ndb.StringProperty(choices=['undergraduate', 'graduate'])
    program = ndb.KeyProperty(kind=Program)
    yearOffered = ndb.IntegerProperty()
    monthOffered = ndb.StringProperty(choices=['January',
                                               'February',
                                               'March',
                                               'April',
                                               'May',
                                               'June',
                                               'July',
                                               'August',
                                               'September',
                                               'October',
                                               'November',
                                               'December'])
    # Attribution for this course
    attribution = ndb.TextProperty()


class Exercise(ndb.Model):
    # Exercise number like
    name = ndb.StringProperty()
    number = ndb.StringProperty()
    course = ndb.KeyProperty(kind=Course)

    def __unicode__(self):
        return self.name


class Challenge(ndb.Model):
    """Models a challenge"""
    EMPTY_MARKDOWN = 'Complete me!'

    name_persistent = ndb.StringProperty(verbose_name="Name")

    def get_name(self):
        if self.name_persistent:
            return self.name_persistent
        elif self.exercise and self.exercise.name:
            self.name_persistent = self.exercise.name
            self.put()
            return self.name_persistent

    def set_name(self, value):
        self.name_persistent = value

    name = property(get_name, set_name, "name")

    # compiled markdown
    content = ndb.TextProperty()
    # non-compiled markdown
    markdown = ndb.TextProperty(default=EMPTY_MARKDOWN)

    template_code = ndb.StringProperty()
    attribution_persistent = ndb.TextProperty(verbose_name="attribution")

    # one to one relationship
    exercise = ndb.KeyProperty(kind=Exercise)

    # true iff this challenge is to be reviewed by the server
    automatic_review = ndb.BooleanProperty()

    # true if this challenge has public submissions
    public_submissions = ndb.BooleanProperty(default=False)

    # the course breadcrumb
    breadcrumb_persisted = ndb.StringProperty(verbose_name="breadcrumb")

    #pdf controls
    pdf_url = ndb.StringProperty()
    pdf_startpage = ndb.StringProperty()
    pdf_endpage = ndb.StringProperty()
    pdf_startoffset = ndb.StringProperty()
    pdf_endoffset = ndb.StringProperty()

    # stats
    num_jeeqsers_solved = ndb.IntegerProperty(default=0)
    num_jeeqsers_submitted = ndb.IntegerProperty(default=0)

    # number of submissions to this challenge that still need reviewing!
    submissions_without_review = ndb.IntegerProperty(default=0)
    last_solver = ndb.KeyProperty(kind=Jeeqser)
    last_solver_picture_url_persisted = ndb.StringProperty()

    def get_breadcrumb(self):
        if self.breadcrumb_persisted:
            return self.breadcrumb_persisted
        else:
            self.breadcrumb_persisted = self.exercise.number\
                + ' > ' + self.exercise.course.name\
                + ' > ' + self.exercise.course.program.name\
                + ' > ' + self.exercise.course.program.university.name
            self.put()
            return self.breadcrumb_persisted

    breadcrumb = property(fget=get_breadcrumb, doc="Course Breadcrumb")

    # exercise relate info
    exercise_number_persisted = ndb.StringProperty()
    exercise_program_persisted = ndb.StringProperty()
    exercise_university_persisted = ndb.StringProperty()
    exercise_course_code_persisted = ndb.StringProperty()
    exercise_course_name_persisted = ndb.StringProperty()

    @property
    def exercise_number(self):
        """Exercise Number"""
        if self.exercise_number_persisted:
            return self.exercise_number_persisted
        else:
            if self.exercise:
                self.exercise_number_persisted = self.exercise.number
                self.put()
                return self.exercise_number_persisted
            else:
                return None

    @property
    def exercise_program(self):
        """Exercise Program"""
        if self.exercise_program_persisted:
            return self.exercise_program_persisted
        else:
            if self.exercise:
                self.exercise_program_persisted = self.exercise.\
                    course.\
                    program.\
                    name
                self.put()
                return self.exercise_program_persisted
            else:
                return None

    @property
    def exercise_university(self):
        """ Exercise University """
        if self.exercise_university_persisted:
            return self.exercise_university_persisted
        else:
            if self.exercise:
                self.exercise_university_persisted = self.exercise.\
                    course.\
                    program.\
                    university.\
                    name
                self.put()
                return self.exercise_university_persisted
            else:
                return None

    @property
    def attribution(self):
        """Attribution"""
        if self.attribution_persistent:
            return self.attribution_persistent
        elif self.exercise and self.exercise.course.attribution:
            self.attribution_persistent = self.exercise.course.attribution
            self.put()
            return self.attribution_persistent

    @attribution.setter
    def set_attribution(self, value):
        self.attribution_persistent = value

    @property
    def exercise_course_code(self):
        if self.exercise_course_code_persisted:
            return self.exercise_course_code_persisted
        elif self.exercise and self.exercise.course:
            self.exercise_course_code_persisted = self.exercise.course.code
            self.put()
            return self.exercise_course_code_persisted

    @property
    def exercise_course_name(self):
        if self.exercise_course_name_persisted:
            return self.exercise_course_name_persisted
        elif self.exercise and self.exercise.name:
            self.exercise_course_name_persisted = self.exercise.course.name
            self.put()
            return self.exercise_course_name_persisted

    @property
    def last_solver_picture_url(self):
        if self.last_solver_picture_url_persisted:
            return self.last_solver_picture_url_persisted
        elif self.last_solver:
            self.last_solver_picture_url_persisted = \
                self.last_solver.profile_url
            self.put()
            return self.last_solver_picture_url_persisted
        else:
            return None

    @last_solver_picture_url.setter
    def last_solver_picture_url(self, value):
        self.last_solver_picture_url_persisted = value

    def update_last_solver(self, solver):
        """
        updates the last solver for this challenge
        """
        # TODO: need to queue a task for updating the last_solver when
        # given solver is none and needs to be computed.
        self.last_solver = solver.key if solver else None
        self.last_solver_picture_url = solver.profile_url if solver else None

    @property
    def testcases(self):
        return TestCase.query()\
            .filter(TestCase.challenge == self.key)\
            .fetch(MAX_FETCH)

    def get_num_jeeqsers_solved(self):
        """Get num_jeeqsers_solved as a direct DB query.

        num_jeeqsers_solved itself is updated manually during submission.

        """

        return Jeeqser_Challenge.query()\
            .filter(Jeeqser_Challenge.challenge == self.key)\
            .filter(Jeeqser_Challenge.status == AttemptStatus.SUCCESS)\
            .count()

    def get_num_jeeqsers_submitted(self):
        """Get num_jeeqsers_submitted as a direct DB query.

        num_jeeqsers_submitted itself is updated manually during submission.

        """

        return Jeeqser_Challenge.query()\
            .filter(Jeeqser_Challenge.challenge == self.key)\
            .count()

    def get_submissions_without_review(self):
        """Get submissions_without_review as a direct DB query.

        submissions_without_review itself is updated manually during
        submission.

        """

        return Attempt.query().\
            filter(Attempt.challenge == self.key).\
            filter(Attempt.active == True).\
            filter(Attempt.review_count == 0).\
            count()


class Draft(ndb.Model):
    """Models a draft (un-submitted) attempt"""
    challenge = ndb.KeyProperty(kind=Challenge)
    author = ndb.KeyProperty(kind=Jeeqser)
    # compiled markdown
    content = ndb.TextProperty()
    # non-compiled markdown
    markdown = ndb.TextProperty()
    date = ndb.DateTimeProperty(auto_now=True)


class Attempt(ndb.Model):
    """Models a Submission for a Challenge """
    challenge = ndb.KeyProperty(kind=Challenge)
    author = ndb.KeyProperty(kind=Jeeqser)
    # compiled markdown
    content = ndb.TextProperty()
    # non-compiled markdown
    markdown = ndb.TextProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    stdout = ndb.StringProperty()
    stderr = ndb.StringProperty()
    # List of users who reviewed this submission
    users_reviewed = ndb.KeyProperty(repeated=True)
    review_count = ndb.IntegerProperty(default=0)

    correct_count = ndb.IntegerProperty(default=0)
    incorrect_count = ndb.IntegerProperty(default=0)
    flag_count = ndb.IntegerProperty(default=0)
    # Status of jeeqser's submission for this challenge
    # a challenge is solved if correct_count > incorrect_count + flag_count
    status = ndb.StringProperty(
        choices=[AttemptStatus.SUCCESS, AttemptStatus.FAIL])

    # feedback score quantization TODO: might be removed !?
    feedback_score_sum = ndb.FloatProperty(default=float(0))
    feedback_score_average = ndb.FloatProperty(default=float(0))

    # is this the active submission for review ?
    active = ndb.BooleanProperty(default=False)

    # the index of this attempt among all attempts for a challenge.
    index = ndb.IntegerProperty(default=0)

    # Spam ?
    flagged_by = ndb.KeyProperty(repeated=True)
    # if True, this attempt is blocked. Become true, once flag_count goes
    # above a threshold
    flagged = ndb.BooleanProperty(default=False)

    IS_LIKED = 'liked'
    IS_DISLIKED = 'disliked'
    liked = ndb.KeyProperty(repeated=True)
    disliked = ndb.KeyProperty(repeated=True)
    likes_total = ndb.IntegerProperty(default=0)

    @property
    def feedbacks(self):
        return Feedback.query()\
            .filter(Feedback.attempt == self)\
            .fetch(MAX_FETCH)


class Jeeqser_Challenge(ndb.Model):
    """
    Represents the relation between a Jeeqser and a Challenge
    Exists in the same entity group as the jeeqser
    """

    jeeqser = ndb.KeyProperty(kind=Jeeqser)
    challenge = ndb.KeyProperty(kind=Challenge)
    active_attempt = ndb.KeyProperty(kind=Attempt)

    # review counts for the active attempt
    # (denormalized from the active attempt)
    correct_count = ndb.IntegerProperty(default=0)
    incorrect_count = ndb.IntegerProperty(default=0)
    flag_count = ndb.IntegerProperty(default=0)
    # Status of jeeqser's submission for this challenge
    # a challenge is solved if correct_count > incorrect_count + flag_count
    status = ndb.StringProperty(
        choices=[AttemptStatus.SUCCESS, AttemptStatus.FAIL])
    status_changed_on = ndb.DateTimeProperty()


class Review:
    CORRECT = 'correct'
    INCORRECT = 'incorrect'
    GENIUS = 'genius'
    FLAG = 'flag'


class Feedback(ndb.Model):
    """Models feedback for submission
     Belongs to the same entity group as the attempt for which it is for.
    """

    attempt = ndb.KeyProperty(kind=Attempt)
    author = ndb.KeyProperty(kind=Jeeqser)
    # Denormalizing the attempt author
    attempt_author = ndb.KeyProperty(kind=Jeeqser)
    markdown = ndb.TextProperty()
    content = ndb.TextProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    review = ndb.StringProperty(
        choices=[Review.CORRECT, Review.INCORRECT, Review.GENIUS, Review.FLAG])

    # Spam ?
    flagged_by = ndb.KeyProperty(repeated=True)
    flag_count = ndb.IntegerProperty(default=0)
    # if True, this feedback is blocked. Becomes true, once flag_count goes
    # above a threshold
    flagged = ndb.BooleanProperty(default=False)


class TestCase(ndb.Model):
    """ Models a test case"""
    challenge = ndb.KeyProperty(kind=Challenge)
    statement = ndb.StringProperty()
    expected = ndb.StringProperty()


class Activity(ndb.Model):
    """Models an activity done on Jeeqs
       Parent: Jeeqser who performed this Activity
    """
    # TODO remove voting after migration
    type = ndb.StringProperty(choices=[
        'submission', 'voting', 'reviewing', 'flagging'])
    done_by = ndb.KeyProperty(kind=Jeeqser)
    done_by_displayname = ndb.StringProperty()
    done_by_gravatar = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)

    challenge = ndb.KeyProperty(kind=Challenge)
    challenge_name = ndb.StringProperty()  # denormamlize from challenge

    submission = ndb.KeyProperty(kind=Attempt)
    submission_author = ndb.KeyProperty(kind=Jeeqser)
    submission_author_displayname = ndb.StringProperty()
    submission_author_gravatar = ndb.StringProperty()

    feedback = ndb.KeyProperty(kind=Feedback)


def get_jeeqser_challenge(
        jeeqser_key,
        challenge_key,
        create=False,
        submission_key=None):
    """
    Get a Jeeqser_Challenge entity by key
    :param jeeqser_key: jeeqser's key
    :param challenge_key:  challenge's key
    :param create: create entity if not found
    """
    results = Jeeqser_Challenge\
        .query(ancestor=jeeqser_key)\
        .filter(Jeeqser_Challenge.jeeqser == jeeqser_key)\
        .filter(Jeeqser_Challenge.challenge == challenge_key)\
        .fetch(1)
    if len(results) == 0 and create:
    # should never happen but let's guard against it!
        logging.error("Jeeqser_Challenge not available! for jeeqser : "
                      + jeeqser_key.get().user.email()
                      + " and challenge : "
                      + challenge_key.get().name)
        jc = Jeeqser_Challenge(
            parent=jeeqser_key,
            jeeqser=jeeqser_key,
            challenge=challenge_key,
            active_attempt=submission_key)
        jc.put()
        return jc
    elif len(results) > 0:
        return results[0]
    else:
        return None

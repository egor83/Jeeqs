#!/usr/bin/python

"""
Model for challenges and solutions.

In order to backup the local data store, first create DataStore stats using the local Admin console and then
run the following command:

These commands are working on Python 2.5.4 as of now. There are known issues with default installations of
python on MacOS and serialization of floats.

Download from local datastore into a file
appcfg.py download_data --url=http://jeeqsy.appspot.com/_ah/remote_api --filename=[db_backup_2012_May_19th] --application=s~jeeqsy

Upload from a file into production:
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
     if att.vote_count == 0:
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
...     if att.active and att.vote_count == 0:
...        unreviewed +=1
...   ch.submissions_without_review = unreviewed
...   ch.put()
...


"""

from google.appengine.ext import db
from google.appengine.ext import ndb
from gravatar import get_profile_url

class Jeeqser(db.Model):
    """ A Jeeqs User """
    user = db.UserProperty()
    displayname_persisted = db.StringProperty()
    reviews_out_num = db.IntegerProperty(default=0)
    reviews_in_num = db.IntegerProperty(default=0)
    submissions_num = db.IntegerProperty(default=0)
    correct_submissions_count_persisted = db.IntegerProperty()
    gravatar_url_persisted = db.LinkProperty()
    gplus_picture_url = db.LinkProperty()
    profile_url_persisted = db.LinkProperty()
    is_moderator = db.BooleanProperty()
    took_tour = db.BooleanProperty()
    suspended_until = db.DateTimeProperty()
    unaccounted_flag_count = db.IntegerProperty(default=0)
    # Total number of posts by this user that are flagged
    total_flag_count = db.IntegerProperty(default=0)

    #Flag limits
    last_flagged_on = db.DateTimeProperty()
    # Number of posts this jeeqser has flagged today
    num_flagged_today = db.IntegerProperty()

    @property
    def correct_submissions_count(self):
        if not self.correct_submissions_count_persisted:
            # calculate submissions that are correct by this Jeqeqser
            correct_count = Jeeqser_Challenge.all().filter('jeeqser = ', self).filter('status = ', 'correct').count()
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
        if self.displayname_persisted is None:
            self.displayname_persisted = self.user.nickname().split('@')[0]
            self.put()
        return self.displayname_persisted

    def set_displayname(self, value):
        self.displayname_persisted = value

    # Proxy for persisted displayname # TODO: upgrade to property decorator in python 2.7
    displayname = property(get_displayname, set_displayname, "Display name")

    def get_gravatar_url(self):
        if self.gravatar_url_persisted is None:
            self.gravatar_url_persisted = get_profile_url(self.user.email())
            self.put()
        return self.gravatar_url_persisted

    def set_gravatar_url(self, value):
        self.gravatar_url_persisted = value

    gravatar_url = property(get_gravatar_url, set_gravatar_url, "Gravatar URL")

    @classmethod
    def get_review_user(cls):
        # return jeeqser.moderator
        return Jeeqser.get('agpkZXZ-amVlcXN5cg8LEgdKZWVxc2VyGMGpBww')

""" University program course exercise in NDB:
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
    monthOffered = ndb.StringProperty(choices=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'Auguest', 'September', 'October', 'November', 'December'])
    # Attribution for this course
    attribution = ndb.TextProperty()

class Exercise(ndb.Model):
    # Exercise number like
    name = ndb.StringProperty()
    number = ndb.StringProperty()
    course = ndb.KeyProperty(kind=Course)

    def __unicode__(self):
        return self.name
"""

class University(db.Model):
    name = db.StringProperty()
    fullname = db.StringProperty()

class Program(db.Model):
    name = db.StringProperty()
    fullname = db.StringProperty()
    university = db.ReferenceProperty(University, collection_name='programs')

class Course(db.Model):
    name = db.StringProperty()
    code = db.StringProperty()
    description = db.TextProperty()
    level = db.StringProperty(choices=['undergraduate', 'graduate'])
    program = db.ReferenceProperty(Program, collection_name='courses')
    yearOffered = db.IntegerProperty()
    monthOffered = db.StringProperty(choices=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'Auguest', 'September', 'October', 'November', 'December'])
    # Attribution for this course
    attribution = db.TextProperty()

class Exercise(db.Model):
    # Exercise number like
    name = db.StringProperty()
    number = db.StringProperty()
    course = db.ReferenceProperty(Course, collection_name='exercises')

    def __unicode__(self):
        return self.name

"""NDB version of challenge:

class Challenge(ndb.Model):
    Models a challenge
    EMPTY_MARKDOWN = 'Complete me!'

    name_persistent = ndb.StringProperty(verbose_name=="Name")

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

    #compiled markdown
    content = ndb.TextProperty()
    #non-compiled markdown
    markdown = ndb.TextProperty(default=EMPTY_MARKDOWN)

    template_code = ndb.StringProperty()
    attribution_persistent = ndb.TextProperty(verbose_name="attribution")

    # one to one relationship
    exercise = ndb.KeyProperty(kind=Exercise)

    # true iff this challenge is to be reviewed by the server
    automatic_review = db.BooleanProperty()

    # true if this challenge has public submissions
    public_submissions = ndb.BooleanProperty(default=False)

    # the course breadcrumb
    breadcrumb_persisted = ndb.StringProperty(verbose_name="breadcrumb")

    #scribd-related info
    document_id = ndb.StringProperty()
    access_key = ndb.StringProperty()
    vertical_scroll = ndb.FloatProperty()

    #stats
    num_jeeqsers_solved = ndb.IntegerProperty(default=0)
    num_jeeqsers_submitted = ndb.IntegerProperty(default=0)
    # number of submissions to this challenge that still need reviewing!
    submissions_without_review = ndb.IntegerProperty(default=0)
    last_solver = ndb.KeyProperty() # TODO: add kind=Jeeqser
    last_solver_picture_url_persisted = ndb.StringProperty()


    def get_breadcrumb(self):
        if self.breadcrumb_persisted:
            return self.breadcrumb_persisted
        else:
            self.breadcrumb_persisted = self.exercise.number \
                                        + ' > ' + self.exercise.course.name \
                                        + ' > ' + self.exercise.course.program.name \
                                        + ' > ' + self.exercise.course.program.university.name
            self.put()
            return self.breadcrumb_persisted

    breadcrumb = property(fget=get_breadcrumb, doc="Course Breadcrumb")

    #exercise relate info
    exercise_number_persisted = ndb.StringProperty()
    exercise_program_persisted = ndb.StringProperty()
    exercise_university_persisted = ndb.StringProperty()
    exercise_course_code_persisted = ndb.StringProperty()
    exercise_course_name_persisted = ndb.StringProperty()

"""

class Challenge(db.Model):
    """Models a challenge"""
    EMPTY_MARKDOWN = 'Complete me!'

    name_persistent = db.StringProperty(verbose_name="Name")

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

    #compiled markdown
    content = db.TextProperty()
    #non-compiled markdown
    markdown = db.TextProperty(default=EMPTY_MARKDOWN)

    template_code = db.StringProperty(multiline=True)
    attribution_persistent = db.TextProperty(verbose_name="attribution")

    # one to one relationship
    exercise = db.ReferenceProperty(Exercise, collection_name='challenge')

    # true iff this challenge is to be reviewed by the server
    automatic_review = db.BooleanProperty()

    # true if this challenge has public submissions
    public_submissions = db.BooleanProperty(default=False)

    # the course breadcrumb
    breadcrumb_persisted = db.StringProperty(verbose_name="breadcrumb")

    #scribd-related info
    document_id = db.StringProperty()
    access_key = db.StringProperty()
    vertical_scroll = db.FloatProperty()

    #stats
    num_jeeqsers_solved = db.IntegerProperty(default=0)
    num_jeeqsers_submitted = db.IntegerProperty(default=0)
    # number of submissions to this challenge that still need reviewing!
    submissions_without_review = db.IntegerProperty(default=0)
    last_solver = db.ReferenceProperty(Jeeqser)
    last_solver_picture_url_persisted = db.LinkProperty()


    def get_breadcrumb(self):
        if self.breadcrumb_persisted:
            return self.breadcrumb_persisted
        else:
            self.breadcrumb_persisted = self.exercise.number \
                                        + ' > ' + self.exercise.course.name \
                                        + ' > ' + self.exercise.course.program.name \
                                        + ' > ' + self.exercise.course.program.university.name
            self.put()
            return self.breadcrumb_persisted

    breadcrumb = property(fget=get_breadcrumb, doc="Course Breadcrumb")

    #exercise relate info
    exercise_number_persisted = db.StringProperty()
    exercise_program_persisted = db.StringProperty()
    exercise_university_persisted = db.StringProperty()
    exercise_course_code_persisted = db.StringProperty()
    exercise_course_name_persisted = db.StringProperty()

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
                self.exercise_program_persisted = self.exercise.course.program.name
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
                self.exercise_university_persisted = self.exercise.course.program.university.name
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
            self.last_solver_picture_url_persisted = self.last_solver.profile_url
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
        self.last_solver = solver
        self.last_solver_picture_url = solver.profile_url if solver else None


class Draft(ndb.Model):
    """Models a draft (un-submitted) attempt"""
    challenge = ndb.KeyProperty() # TODO kind=Challenge
    author = ndb.KeyProperty() # TODO kind=Jeeqser
    #compiled markdown
    content = ndb.TextProperty()
    #non-compiled markdown
    markdown = ndb.TextProperty()
    date = ndb.DateTimeProperty(auto_now=True)

class Attempt(db.Model):
    """Models a Submission for a Challenge """
    challenge = db.ReferenceProperty(Challenge)
    author = db.ReferenceProperty(Jeeqser)
    #compiled markdown
    content = db.TextProperty()
    #non-compiled markdown
    markdown = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    stdout = db.StringProperty(multiline=True)
    stderr = db.StringProperty(multiline=True)
    # List of users who voted for this submission
    users_voted = db.ListProperty(db.Key)
    vote_count = db.IntegerProperty(default=0)

    correct_count = db.IntegerProperty(default=0)
    incorrect_count = db.IntegerProperty(default=0)
    flag_count = db.IntegerProperty(default=0)
    # Status of jeeqser's submission for this challenge
    # a challenge is solved if correct_count > incorrect_count + flag_count
    status = db.StringProperty(choices=['correct', 'incorrect'])

    #vote quantization TODO: might be removed !?
    vote_sum = db.FloatProperty(default=float(0))
    vote_average = db.FloatProperty(default=float(0))

    # is this the active submission for review ?
    active = db.BooleanProperty(default=False)

    # the index of this attempt among all attempts for a challenge.
    index = db.IntegerProperty(default=0)

    # Spam ?
    flagged_by = db.ListProperty(db.Key)
    # if True, this attempt is blocked. Become true, once flag_count goes above a threshold
    flagged = db.BooleanProperty(default=False)

class Jeeqser_Challenge(db.Model):
    """
    Represents the relation between a Jeeqser and a Challenge
    Exists in the same entity group as the jeeqser
    """

    jeeqser = db.ReferenceProperty(Jeeqser)
    challenge = db.ReferenceProperty(Challenge)
    active_attempt = db.ReferenceProperty(Attempt)

    # vote counts for the active attempt (denormalized from the active attempt)
    correct_count = db.IntegerProperty(default=0)
    incorrect_count = db.IntegerProperty(default=0)
    flag_count = db.IntegerProperty(default=0)
    # Status of jeeqser's submission for this challenge
    # a challenge is solved if correct_count > incorrect_count + flag_count
    status = db.StringProperty(choices=['correct', 'incorrect'])
    status_changed_on = db.DateTimeProperty()


class Feedback(db.Model):
    """Models feedback for submission
     Belongs to the same entity group as the attempt for which it is for.
    """

    attempt = db.ReferenceProperty(Attempt, collection_name='feedbacks')
    author = db.ReferenceProperty(Jeeqser, collection_name='feedback_out')
    # Denormalizing the attempt author
    attempt_author = db.ReferenceProperty(Jeeqser, collection_name='feedback_in')
    markdown = db.TextProperty()
    content = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    vote = db.StringProperty(choices=['correct', 'incorrect', 'genius', 'flag'])

    # Spam ?
    flagged_by = db.ListProperty(db.Key)
    flag_count = db.IntegerProperty(default=0)
    # if True, this feedback is blocked. Becomes true, once flag_count goes above a threshold
    flagged = db.BooleanProperty(default=False)

class TestCase(db.Model):
    """ Models a test case"""
    challenge = db.ReferenceProperty(Challenge, collection_name='testcases')
    statement = db.StringProperty(multiline=True)
    expected = db.StringProperty(multiline=True)

class Activity(ndb.Model):
    """Models an activity done on Jeeqs"""
    type= ndb.StringProperty(choices=['submission', 'voting', 'flagging'])
    done_by = ndb.KeyProperty() # TODO kind=Jeeqser
    done_by_displayname = ndb.StringProperty()
    done_by_gravatar = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)

    challenge = ndb.KeyProperty() # TODO kind=Challenge
    challenge_name = ndb.StringProperty() #denormamlize from challenge

    submission = ndb.KeyProperty() # TODO kind=Attempt
    submission_author = ndb.KeyProperty() # TODO: kind=Jeeqser
    submission_author_displayname = ndb.StringProperty()
    submission_author_gravatar = ndb.StringProperty()

    feedback = ndb.KeyProperty() # TODO kind=Feedback



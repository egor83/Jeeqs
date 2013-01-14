import jinja2
import os
from google.appengine.api import users
from models import *
from template_filters import escapejs, timesince
import datetime
import status_code


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.with_'])

jinja_environment.filters['escapejs'] = escapejs
jinja_environment.filters['timesince'] = timesince


def get_jeeqs_robot():
    """
    Returns the robot user that runs tests over programming solutions
    """
    robot = Jeeqser.query().filter(
        Jeeqser.displayname_persisted == 'jeeqs.moderator').fetch(1)[0]
    return robot


def get_jeeqser():
    """
    Gets Jeeqser entity related to the given authenticated user
    """
    user = users.get_current_user()
    if user is None:
        return None

    jeeqsers = Jeeqser.query().filter(Jeeqser.user == user).fetch(1)

    if (len(jeeqsers) == 0):
        jeeqser = Jeeqser(user=user, displayname_persisted=user.nickname())
        jeeqser_id = jeeqser.put().id()
        jeeqser.displayname_persisted = 'user' + str(jeeqser_id)
        jeeqser.put()
        return jeeqser
    return jeeqsers[0]


def add_common_vars(vars):
    vars['local'] = os.environ['APPLICATION_ID'].startswith('dev~')
    vars['isadmin'] = users.is_current_user_admin()
    return vars


def authenticate(required=True):
    """ Authenticates the user and sets self.jeeqser to be the user object.
        The handler object (self) is different for each request.
        so jeeqser should not leak between requests.
        Will return with error if user is not authenticated
    """
    def real_decorator(func):
        def wrapper(self):
            user = users.get_current_user()
            if not user and required:
                self.error(status_code.StatusCode.unauth)
                return
            elif user:
                self.jeeqser = get_jeeqser()
            else:
                self.jeeqser = None

            # clear/check suspension!
            if self.jeeqser and self.jeeqser.suspended_until and \
                    self.jeeqser.suspended_until < datetime.now():
                self.jeeqser.suspended_until = None
                self.jeeqser.put()

            if required and self.jeeqser and self.jeeqser.suspended_until and \
                    self.jeeqser.suspended_until > datetime.now():
                return

            func(self)

        return wrapper
    return real_decorator

# Adds icons and background to feedback objects


def prettify_injeeqs(injeeqs):
    for jeeq in injeeqs:
        if jeeq.vote == Vote.CORRECT:
            jeeq.icon = 'icon-ok'
            jeeq.background = '#EBFFEB'
        elif jeeq.vote == Vote.INCORRECT:
            jeeq.icon = 'icon-remove'
            jeeq.background = '#FFE3E3'
        elif jeeq.vote == Vote.FLAG:
            jeeq.icon = 'icon-flag'
            jeeq.background = 'lightgrey'

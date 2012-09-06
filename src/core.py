import jinja2
import os
from google.appengine.api import users
from models import *
from template_filters import escapejs, timesince

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))
    ,extensions=['jinja2.ext.with_'])

jinja_environment.filters['escapejs'] = escapejs
jinja_environment.filters['timesince'] = timesince


def get_jeeqs_robot():
    """
    Returns the robot user that runs tests over programming solutions
    """
    robot = Jeeqser.all().filter('user =', users.User('a.akhavan.b@gmail.com')).fetch(1)[0]
    return robot

def get_jeeqser():
    """
    Gets Jeeqser entity related to the given authenticated user
    """
    user = users.get_current_user()
    if user is None:
        return None

    jeeqsers = Jeeqser.all().filter('user = ', user).fetch(1)

    if (len(jeeqsers) == 0):
        jeeqser = Jeeqser(user=user, displayname=user.nickname())
        jeeqser.put()
        return jeeqser
    return jeeqsers[0]

def add_common_vars(vars):
    vars['local'] = os.environ['APPLICATION_ID'].startswith('dev~')
    vars['isadmin'] = users.is_current_user_admin();

    return vars


def authenticate(required=True):
    """ Authenticates the user and sets self.jeeqser to be the user object.
        The handler object (self) is different for each request. so jeeqser should not leak between requests.
        Will return with error if user is not authenticated
    """
    def real_decorator(func):
        def wrapper(self):
            user = users.get_current_user()
            if not user and required:
                self.error(StatusCode.unauth)
                return
            elif user:
                self.jeeqser = get_jeeqser()
            else:
                self.jeeqser = None

            # clear/check suspension!
            if self.jeeqser and self.jeeqser.suspended_until and self.jeeqser.suspended_until < datetime.now():
                self.jeeqser.suspended_until = None
                self.jeeqser.put()

            if required and self.jeeqser and self.jeeqser.suspended_until and self.jeeqser.suspended_until > datetime.now():
                return

            func(self)

        return wrapper
    return real_decorator


# Get Jeeqser_Challege for user and challenge
# TODO: move to proper file
def get_JC(jeeqser, challenge):
    return Jeeqser_Challenge\
            .all()\
            .filter('jeeqser =', jeeqser)\
            .filter('challenge =', challenge)\
            .fetch(1)

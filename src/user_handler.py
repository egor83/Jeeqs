from core import *
from google.appengine.api import users
from oauth2 import service, decorator
from apiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError
import webapp2
from utils import StatusCode


class UserHandler(webapp2.RequestHandler):
    """Renders User's profile page"""

    @authenticate(False)
    @decorator.oauth_aware
    def get(self):
        jeeqser_key = self.request.get('jk')

        # target_jeeqser is the jeeqser for which the stats will be generated
        target_jeeqser = None

        has_credentials = decorator.has_credentials()

        if jeeqser_key:
            target_jeeqser = Jeeqser.get(jeeqser_key)
            if not target_jeeqser:
                self.error(StatusCode.forbidden)
                return

        elif self.jeeqser:
            target_jeeqser = self.jeeqser

            if not self.jeeqser.gplus_picture_url:
                if decorator.has_credentials() and not self.jeeqser.gplus_picture_url:
                    try:
                        http = decorator.http()
                        user = service.people().get(userId='me').execute(http)
                        self.jeeqser.gplus_picture_url = user['image']['url']
                        self.jeeqser.put()

                    except (AccessTokenRefreshError, HttpError):
                        has_credentials = False
                        pass
        else:
            self.redirect('/')

        # get challenge history for target_jeeqser
        # TODO: needs pagination
        correct_jcs = Jeeqser_Challenge\
                        .all()\
                        .filter('jeeqser = ', target_jeeqser)\
                        .filter('status = ', 'correct')\
                        .order('-status_changed_on')\
                        .fetch(100)
        # pre-fetch the challenges
        for jc in correct_jcs:
            jc.challenge.key()

        vars = add_common_vars({
            'jeeqser' : self.jeeqser,
            'target_jeeqser' : target_jeeqser,
            'login_url': users.create_login_url(self.request.url),
            'logout_url': users.create_logout_url(self.request.url),
            'google_plus_auth_url': decorator.authorize_url(),
            'has_google_plus_credentials': has_credentials,
            'correct_jcs' : correct_jcs,
            })

        template = jinja_environment.get_template('Jeeqser.html')
        rendered = template.render(vars)
        self.response.write(rendered)
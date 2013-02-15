import os
import string

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import core
from models import *


class ChallengePage(webapp.RequestHandler):
    """
    Create a new challenge
    """
    @core.authenticate(required=True)
    def get(self):
        all_courses = Course.query().fetch(1000)

        vars = core.add_common_vars({
            'courses': all_courses,
            'jeeqser': self.jeeqser,
            'login_url': users.create_login_url(self.request.url),
            'logout_url': users.create_logout_url(self.request.url)
        })

        template = core.jinja_environment.get_template('new_challenge.html')
        rendered = template.render(vars)
        self.response.out.write(rendered)

    @core.authenticate(required=True)
    def post(self):
        course = Course.get(self.request.get('course'))
        self.response.out.write(course.name)
        number = self.request.get('number')
        name = string.capwords(self.request.get('name'))
        markdown = self.request.get('markdown')
        template_code = self.request.get('template_code')
        document_id = self.request.get('document_id')
        access_key = self.request.get('access_key')

        exercise = Exercise(number=number, name=name, course=course)
        exercise.put()

        challenge = Challenge(
            name_persistent=name,
            markdown=markdown,
            template_code=template_code,
            exercise=exercise,
            document_id=document_id,
            access_key=access_key)

        challenge.put()

        self.redirect('/admin/challenges/new')


class ChallengeListPage(webapp.RequestHandler):
    def get(self):
        query = Challenge.all().fetch(1000)
        for item in query:
            self.response.out.write(
                '<a href="/admin/challenges/edit?key=%s">Edit</a> '
                % item.key())
            number = item.exercise.number if item.exercise else '--'
            self.response.out.write("%s %s <br>" % (number, item.name))

        self.response.out.write(
            '<br/><a href="/admin/challenges/new">New Challenge</a>')


def main():
    application = webapp.WSGIApplication(
        [('/admin/challenges/new', ChallengePage),
            ('/admin/challenges', ChallengeListPage),
            ('/admin/challenges/', ChallengeListPage),
         ],
        debug=True)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

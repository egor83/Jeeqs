import os
import string

from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import core
from models import *


class EditChallengePage(webapp.RequestHandler):
    @core.authenticate(required=True)
    def get(self):
        challenge = None
        page_vars = {}
        challenge_key = self.request.get('ch')
        if challenge_key:
            challenge = ndb.Key(urlsafe=challenge_key).get()
        if challenge:
            page_vars['challenge'] = challenge

        vars = core.add_common_vars(page_vars)

        template = core.jinja_environment.get_template('admin_challenge.html')
        rendered = template.render(vars)
        self.response.out.write(rendered)

    def post(self):
        challenge = None
        challenge_key = self.request.get('ch')
        if challenge_key:
            challenge = ndb.Key(urlsafe=challenge_key).get()
        if challenge:
            challenge.exercise_number_persisted = self.request.get('number')
            challenge.name_persistent = self.request.get('name')
            challenge.markdown = self.request.get('markdown')
            challenge.template_code = self.request.get('template_code')
            challenge.pdf_url = self.request.get('pdf_url')
            challenge.pdf_startpage = self.request.get('pdf_startpage')
            challenge.pdf_endpage = self.request.get('pdf_endpage')
            challenge.pdf_startoffset = self.request.get('pdf_startoffset')
            challenge.pdf_endoffset = self.request.get('pdf_endoffset')
            challenge.put()
            self.redirect('/challenge/?ch=' + challenge_key)
        else:
            self.response.out.write('something went wrong!')


class AddChallengePage(webapp.RequestHandler):
    """
Create a new challenge
"""
    @core.authenticate(required=True)
    def get(self):
        all_courses = Course.query().fetch()
        page_vars = {
            'courses': all_courses,
            'jeeqser': self.jeeqser,
            'login_url': users.create_login_url(self.request.url),
            'logout_url': users.create_logout_url(self.request.url)
        }

        vars = core.add_common_vars(page_vars)

        template = core.jinja_environment.get_template('admin_challenge.html')
        rendered = template.render(vars)
        self.response.out.write(rendered)

    @core.authenticate(required=True)
    def post(self):
        course = None
        number = None
        if self.request.get('course') != '':
            course = ndb.Key(urlsafe=self.request.get('course'))
            number = self.request.get('number')
        name = string.capwords(self.request.get('name'))

        #pdf controls
        pdf_url = self.request.get('pdf_url')
        pdf_startpage = self.request.get('pdf_startpage')
        pdf_endpage = self.request.get('pdf_endpage')
        pdf_startoffset = self.request.get('pdf_startoffset')
        pdf_endoffset = self.request.get('pdf_endoffset')

        markdown = self.request.get('markdown')
        template_code = self.request.get('template_code')
        exercise_key=None
        if number and course:
            exercise = Exercise(number=number, name=name, course=course)
            exercise_key = exercise.put()
            challenge = Challenge(
                name_persistent=name,
                markdown=markdown,
                pdf_url=pdf_url,
                pdf_startpage=pdf_startpage,
                pdf_endpage=pdf_endpage,
                pdf_startoffset=pdf_startoffset,
                pdf_endoffset=pdf_endoffset,
                template_code=template_code,
                exercise=exercise_key,
                course=course)
        else:
            challenge = Challenge(
                name_persistent=name,
                markdown=markdown,
                pdf_url=pdf_url,
                pdf_startpage=pdf_startpage,
                pdf_endpage=pdf_endpage,
                pdf_startoffset=pdf_startoffset,
                pdf_endoffset=pdf_endoffset,
                template_code=template_code)

        challenge.put()
        self.redirect('/admin/challenges/new')


class ChallengeListPage(webapp.RequestHandler):
    def get(self):
        query = Challenge.query().fetch(1000)
        for item in query:
            self.response.out.write(
                '<a href="/admin/challenges/edit?ch=%s">Edit</a> '
                % item.key.urlsafe())
            number = item.exercise.get().number if item.exercise else '--'
            self.response.out.write("%s %s <br>" % (number, item.name))

        self.response.out.write(
            '<br/><a href="/admin/challenges/new">New Challenge</a>')


def main():
    application = webapp.WSGIApplication(
        [
            ('/admin/challenges/new', AddChallengePage),
            ('/admin/challenges/edit', EditChallengePage),
            ('/admin/challenges', ChallengeListPage),
            ('/admin/challenges/', ChallengeListPage),
            ],
        debug=True)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

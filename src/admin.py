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
        redirect_to = self.request.referer
        challenge = None
        page_vars = {'redirect_to':redirect_to}
        challenge_key = self.request.get('ch')
        if challenge_key:
            challenge = ndb.Key(urlsafe=challenge_key).get()
        if challenge:
            page_vars['challenge'] = challenge

        vars = core.add_common_vars(page_vars)

        template = core.jinja_environment.get_template('admin_challenge.html')
        rendered = template.render(vars)
        self.response.out.write(rendered)

    @core.authenticate(required=True)
    #@ndb.transactional(xg=True)
    def post(self):
        redirect_to = self.request.get('redirect_to')
        challenge = None
        course = None
        old_number = None
        old_name = None
        challenge_key = self.request.get('ch')
        number = self.request.get('number')
        name = self.request.get('name')
        challenge = ndb.Key(urlsafe=challenge_key).get()
        if challenge.exercise:
            course = challenge.exercise.get().course
        if challenge.exercise:
            old_number = challenge.exercise.get().number
            old_name = challenge.exercise.get().name
        if challenge:
            challenge.exercise_number_persisted = number
            challenge.name_persistent = name
            challenge.markdown = self.request.get('markdown')
            challenge.template_code = self.request.get('template_code')
            challenge.pdf_url = self.request.get('pdf_url')
            challenge.pdf_startpage = self.request.get('pdf_startpage')
            challenge.pdf_endpage = self.request.get('pdf_endpage')
            challenge.pdf_startoffset = self.request.get('pdf_startoffset')
            challenge.pdf_endoffset = self.request.get('pdf_endoffset')
            challenge_key = challenge.put()
            if (old_name != name or old_number != number) and challenge.exercise:
                exercise = Exercise.query().\
                    filter(Exercise.number == old_number).\
                    filter(Exercise.name == old_name).\
                    filter(Exercise.course == course).get()
                exercise.name = name
                exercise.number = number
                exercise.put()
            self.redirect(redirect_to)
        else:
            self.response.out.write('something went wrong!')


class AddChallengePage(webapp.RequestHandler):
    """
Create a new challenge
"""
    @core.authenticate(required=True)
    def get(self):
        redirect_to = self.request.referer
        all_courses = Course.query().fetch()
        page_vars = {
            'redirect_to':redirect_to,
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
        redirect_to = self.request.get('redirect_to')
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

        challenge_key = challenge.put()
        self.redirect(redirect_to)


class ChallengeListPage(webapp.RequestHandler):
    def get(self):
        query = Challenge.query().fetch(1000)
        self.response.out.write(
            '<br/><a href="/admin/challenges/new">New Challenge</a><br><br><br>')
        for item in query:
            self.response.out.write(
                '<a href="/admin/challenges/edit?ch=%s">Edit</a> '
                % item.key.urlsafe())
            number = item.exercise.get().number if item.exercise else '--'
            self.response.out.write("%s %s <br>" % (number, item.name))




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

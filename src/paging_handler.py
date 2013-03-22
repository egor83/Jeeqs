from models import *
import jeeqs_request_handler
import core


class FeedbacksPagingHandler(jeeqs_request_handler.JeeqsRequestHandler):
    FEEDBACKS_PER_PAGE = 5

    def getFeedbacksForJeeqser(self, jeeqserKey):
        qo = ndb.QueryOptions()

        feedbacks_query = Feedback \
            .query() \
            .filter(Feedback.attempt_author == jeeqserKey) \
            .filter(Feedback.flagged == False) \
            .order(Feedback.flag_count) \
            .order(-Feedback.date)

        cursor = "None"
        if self.request.get('cursor'):
            cursor = self.request.get('cursor')

        if cursor and cursor != "None":
            # a cursor was passed along with the request, we're in
            # the middle of the list of attempts, show "Newer" button
            # to navigate to the newer attempts
            qo = ndb.QueryOptions(start_cursor=ndb.Cursor(urlsafe=cursor))
            has_newer = True
        else:
            # no cursor was passed, we are at the beginning of the list
            # of attempts already and shouldn't display "Newer" button
            qo = ndb.QueryOptions()
            has_newer = False

        feedbacks, cursor, more = feedbacks_query.fetch_page(self.FEEDBACKS_PER_PAGE, options=qo)
        core.prettify_injeeqs(feedbacks)

        if cursor and more:
            cursor = cursor.urlsafe()
        else:
            cursor = ''

        return feedbacks, cursor, has_newer

    def getFeedbacksForSubmission(self, jeeqserKey, submissionKey):
        feedbacks_query = Feedback.query() \
            .filter(Feedback.attempt == submissionKey) \
            .filter(Feedback.flagged == False) \
            .order(Feedback.flag_count) \
            .order(-Feedback.date)

        cursor = "None"
        if self.request.get('cursor'):
            cursor = self.request.get('cursor')

        if cursor and cursor != "None":
            # a cursor was passed along with the request, we're in
            # the middle of the list of attempts, show "Newer" button
            # to navigate to the newer attempts
            qo = ndb.QueryOptions(start_cursor=ndb.Cursor(urlsafe=cursor))
            has_newer = True
        else:
            # no cursor was passed, we are at the beginning of the list
            # of attempts already and shouldn't display "Newer" button
            qo = ndb.QueryOptions()
            has_newer = False

        feedbacks, cursor, more = feedbacks_query.fetch_page(self.FEEDBACKS_PER_PAGE, options=qo)
        core.prettify_injeeqs(feedbacks)

        if cursor and more:
            cursor = cursor.urlsafe()
        else:
            cursor = ''

        return feedbacks, cursor, has_newer

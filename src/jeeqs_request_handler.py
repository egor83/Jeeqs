import webapp2
import status_code

class JeeqsRequestHandler(webapp2.RequestHandler):
  """
  Base class for Jeeqs request handlers.
  """
  def getValueInQuery(self, param_name, required=True):
    """
    Returns the value for the given parameter name in the query string.
    If the parameter does not exist, raises Exception
    :param param_name: The name of the parameter in the query.
    :param required If the parameter is required
    :return: Value for the given parameter.
    """
    value = self.request.get(param_name)
    if value == '' and required:
      self.abort(
        status_code.StatusCode.bad,
        "missing parameter %s" % param_name)
    return value

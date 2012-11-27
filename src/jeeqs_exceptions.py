import exceptions

class JeeqsException(exceptions.Exception):
  pass

class ReviewerNotQualified(JeeqsException):
  pass

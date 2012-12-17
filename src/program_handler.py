import jeeqs_request_handler
import program_tester

class ProgramHandler(jeeqs_request_handler.JeeqsRequestHandler):
  """Evaluates a python program and returns the result.
  """
  def get(self):
    program = self.getValueInQuery('program')
    self.response.headers['Content-Type'] = 'text/plain'
    output, module = program_tester.compile_and_run(program)
    self.response.write(output)

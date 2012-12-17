import jeeqs_test
import program_tester
import mox

__author__ = 'nomadali'

class ProgramTesterTestCase(jeeqs_test.JeeqsTestCase):
  def setUp(self):
    jeeqs_test.JeeqsTestCase.setUp(self)

  def tearDown(self):
    jeeqs_test.JeeqsTestCase.tearDown(self)

  def test_compile_and_run_pass(self):
    """test compile_and_run "pass"."""
    program = 'pass'
    output, program_module = program_tester.compile_and_run(program)
    self.assertEquals(output, "")
    self.assertIsNotNone(program_module)

  def test_compile_and_run_compile_error(self):
    """test compile_and_run "pass"."""
    program = 'error!'
    output, program_module = program_tester.compile_and_run(program)
    self.assertIsNone(program_module)
    self.assertTrue('Compile error' in output)

  def test_compile_and_run_factorial(self):
    program = '''
def factorial(n):
  return 1 if n == 1 else n * factorial(n-1)

    '''
    output, program_module = program_tester.compile_and_run(program)
    self.assertEquals(output, "")
    self.assertIsNotNone(program_module)

  def test_testcases_factorial(self):
    pass

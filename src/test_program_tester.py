import test_jeeqs
import program_tester
import mox

from models import *

__author__ = 'nomadali'

class ProgramTesterTestCase(test_jeeqs.JeeqsTestCase):
  def setUp(self):
    test_jeeqs.JeeqsTestCase.setUp(self)

  def tearDown(self):
    test_jeeqs.JeeqsTestCase.tearDown(self)

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
    program = """
def factorial(n):
  return 1 if n == 1 else n * factorial(n-1)
    """
    challenge = self.CreateChallenge(name_persistent="Factorial")
    TestCase(
        challenge=challenge.key,
        statement="factorial(3)",
        expected="6").put()
    challenge = Challenge.query().filter(
        Challenge.name_persistent == 'Factorial').fetch(1)[0]
    vote, output = program_tester.run_testcases(program, challenge)
    self.assertEquals(vote, Vote.CORRECT)

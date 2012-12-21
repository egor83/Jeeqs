"""
Helps with running test cases over a challenge's solution

"""

# TODO: Add another GAE server for running user submitted programs.

import new
import os
import sys
import StringIO
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

from models import *

def compile_and_run(program):
  """
  Compiles and runs the given program.
  :param program: program to compile and run.
  :return: stdout, stderr,
  """

  output = ""
  # the python compiler doesn't like network line endings.
  program = program.replace('\r\n', '\n')
  # add a couple newlines at the end of the program. this makes
  # single-line expressions such as 'class Foo: pass' evaluate happily.
  program += '\n\n'
  try:
      compiled = compile(program, '<sudmitted>', 'exec')
  except:
      return 'Compile error:  \n' + format_exc(), None
  program_module = new.module('__main__')
  old_main = sys.modules.get('__main__')
  #TODO(majid) Does this properly sandbox the builtins. I can call print!
  #print program_module.__dict__
  try:
    sys.modules['__main__'] = program_module
    program_module.__name__ = '__main__'
    try:
        stdout_buffer = StringIO.StringIO()
        stderr_buffer = StringIO.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = stdout_buffer
            sys.stderr = stderr_buffer
            # allowed imports
            import math
            builtins = {}
            for item in dir(math):
                if hasattr(math.__dict__.get(item), '__call__'):
                    builtins[item] = math.__dict__.get(item)
            program_module.__builtins__ = builtins
            exec compiled in program_module.__dict__
            #exec compiled in {'__builtins__': builtins}, {}
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            output += stdout_buffer.getvalue()
            output += stderr_buffer.getvalue()
    except:
        return 'Execution error: \n' + format_exc(), None
    return output, program_module
  finally:
      sys.modules['__main__'] = old_main

def format_exc():
  etype, value, tb = sys.exc_info()
  #ignore the first frame which is this frame!
  t = ''.join(traceback.format_exception(etype, value, tb)[2:])
  return t #.replace('\n', '  \n').replace(' ', '&nbsp;')

def run_testcases(program, challenge):
  """
  Runs the challenge's test cases over the given program.

  :param program: program to test
  :param challenge: challenge for which the program was submitted
  :return: A vote of correct/incorrect and the output of the test executions.
  """
  success = True
  vote = Vote.CORRECT
  output, program_module = compile_and_run(program)
  if not program_module:
    success = False
    vote = Vote.INCORRECT
  else:
    test_num = 0
    for test in challenge.testcases:
        test_num = test_num + 1
        result = eval(test.statement, program_module.__dict__)
        if not str(result) == test.expected:
            success = False
            output += " Failed with the statement:  \n *****  \n" \
                                + test.statement \
                                + '  \n Expected result:  \n' \
                                + test.expected \
                                + '  \n Actual result:  \n' \
                                + str(result) \
                                + '   \n'
    if test_num == 0:
      output += 'No test cases to run!'
    elif success:
      output = 'Success! All tests ran successfully!' + output
    else:
      output = 'At least one of the test cases failed: ' + output
      vote = Vote.INCORRECT
  return vote, output


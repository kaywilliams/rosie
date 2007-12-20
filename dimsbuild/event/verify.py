import sys
import time
import unittest

from dims import pps

from dimsbuild.logging import L1, L2
from dimsbuild.verify  import BuildTestResult

class VerifyMixin:
  def __init__(self):
    self.verifier = VerifyObject(self)

  def verify(self):
    self.verifier.unittest()

class VerifyObject(unittest.TestCase):
  "Dummy class to contain verify-related methods"
  def __init__(self, ptr):
    self.ptr = ptr
    self.logger = self.ptr.logger
    self.method_prefix = 'verify_'
    self._testMethodName = None
    self._testMethodDoc = None

  def failIfExists(self, path):
    self.failIf(pps.Path(path).exists(), "'%s' exists" % path)
  def failUnlessExists(self, path):
    self.failUnless(pps.Path(path).exists(), "'%s' does not exist " % path)

  def unittest(self):
    methods = [] # list of methods to run
    for attr in dir(self.ptr):
      if not attr.startswith(self.method_prefix): continue
      method = getattr(self.ptr, attr)
      if not callable(method): continue
      methods.append(method)

    result = BuildTestResult(self.logger)

    if methods:
      self.logger.log(4, L1("running verification methods"))

      starttime = time.time()

      for method in methods:
        fntest = unittest.FunctionTestCase(method)

        result.startTest(fntest)
        try:
          ok = False
          try:
            method()
            ok = True
          except self.failureException:
            result.addFailure(fntest, self._exc_info())
          except KeyboardInterrupt:
            raise
          except:
            result.addError(fntest, self._exc_info())
          if ok:
            result.addSuccess(fntest)
        finally:
          result.stopTest(fntest)

      elapsedtime = time.time() - starttime

      self.logger.log(4, L2("ran %d test%s in %.3fs" %
        (result.testsRun, result.testsRun != 1 and 's' or '', elapsedtime)))

      if not result.wasSuccessful():
        self.logger.log(4, L2("FAILED("), newline=False)
        failed, errored = len(result.failures), len(result.errors)
        if failed:
          self.logger.write(4, "failures=%d" % failed)
        if errored:
          if failed: self.logger.write(4, ", ")
          self.logger.write(4, "errors=%d" % errored)
        self.logger.write(4, ")\n")
        result.printErrors()
      else:
        self.logger.log(4, L2("all tests succeeded"))

    return result

  def _exc_info(self):
    """
    Return a version of sys.exc_info() with the traceback frame
    minimised; usually the top level of the traceback frame is not
    needed.
    """
    exctype, excvalue, tb = sys.exc_info()
    if sys.platform[:4] == 'java': ## tracebacks look different in Jython
      return (exctype, excvalue, tb)
    return (exctype, excvalue, tb)

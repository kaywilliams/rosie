import time
import unittest

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

  def shortDescription(self):
    return self._testMethodDoc.split('\n')[0].strip() or None

  def unittest(self):
    methods = [] # list of methods to run
    for attr in dir(self.ptr):
      if not attr.startswith(self.method_prefix): continue
      method = getattr(self.ptr, attr)
      if not callable(method): continue
      methods.append(method)

    if methods:
      self.logger.log(4, L1("running verification methods"))

      starttime = time.time()
      result = BuildTestResult(self.logger)

      for method in methods:
        self._testMethodName = method.__name__
        self._testMethodDoc  = method.__doc__

        result.startTest(self)
        try:
          ok = False
          try:
            method()
            ok = True
          except self.failureException:
            result.addFailure(self, self._exc_info())
          except KeyboardInterrupt:
            raise
          except:
            result.addError(self, self._exc_info())
          if ok:
            result.addSuccess(self)
        finally:
          result.stopTest(self)

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

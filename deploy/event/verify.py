#
# Copyright (c) 2015
# Deploy Foundation. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
import sys
import time
import unittest

from deploy.dlogging import L1, L2
from deploy.util     import pps
from deploy.verify   import BuildTestResult

class VerifyMixin:
  def __init__(self):
    self.method_prefix = 'verify_'

    # dummy pointer to allow access to deploy-specific verify methods
    self.verifier = DeployFunctionTestCase(testFunc=None, ptr=self)

  def verify(self):
    methods = [] # set of methods to run
    for attr in dir(self):
      if not attr.startswith(self.method_prefix): continue
      method = getattr(self, attr)
      if not callable(method): continue
      methods.append(method)

    result = BuildTestResult(self.logger)

    if methods:
      self.logger.log(5, L1("running verification methods"))

      starttime = time.time()

      for method in methods:
        fntest = DeployFunctionTestCase(method, ptr=self)
        fntest.run(result=result)

      elapsedtime = time.time() - starttime

      if not result.wasSuccessful():
        self.logger.log(5, L2("FAILED("), newline=False)
        failed, errored = len(result.failures), len(result.errors)
        if failed:
          self.logger.write(5, "failures=%d" % failed)
        if errored:
          if failed: self.logger.write(5, ", ")
          self.logger.write(5, "errors=%d" % errored)
        self.logger.write(5, ")\n")
        result.printErrors()

    return result


class DeployFunctionTestCase(unittest.FunctionTestCase):
  "child class to contain deploy-specific verify vethods"
  def __init__(self, testFunc, ptr=None):
    unittest.FunctionTestCase.__init__(self, testFunc)
    self.ptr = ptr
    self._testMethodDoc = None

  def failUnlessSet(self, cvar):
    self.failUnless(self.ptr.cvars[cvar] is not None, "'%s' cvar not set" % cvar)
  def failIfExists(self, path):
    self.failIf(pps.path(path).exists(), "'%s' exists" % path)
  def failUnlessExists(self, path):
    self.failUnless(pps.path(path).exists(), "'%s' does not exist " % path)

  def run(self, result=None):
    result.startTest(self)
    testMethod = getattr(self, self._testMethodName)
    try:
      ok = False
      try:
        testMethod()
        ok = True
      except self.failureException:
        result.addFailure(self._testMethodName, self._exc_info())
      except KeyboardInterrupt:
        raise
      except:
        result.addError(self, self._exc_info())
      if ok:
        result.addSuccess(self)
    finally:
      result.stopTest(self)

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

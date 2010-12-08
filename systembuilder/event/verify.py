#
# Copyright (c) 2010
# Rendition Software, Inc. All rights reserved.
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

from systembuilder.util import pps

from systembuilder.logging import L1, L2
from systembuilder.verify  import BuildTestResult

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

  def failUnlessSet(self, cvar):
    self.failUnless(self.ptr.cvars[cvar] is not None, "'%s' cvar not set" % cvar)
  def failIfExists(self, path):
    self.failIf(pps.path(path).exists(), "'%s' exists" % path)
  def failUnlessExists(self, path):
    self.failUnless(pps.path(path).exists(), "'%s' does not exist " % path)

  def unittest(self):
    methods = [] # list of methods to run
    for attr in dir(self.ptr):
      if not attr.startswith(self.method_prefix): continue
      method = getattr(self.ptr, attr)
      if not callable(method): continue
      methods.append(method)

    result = BuildTestResult(self.logger)

    if methods:
      self.logger.log(5, L1("running verification methods"))

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

#
# Copyright (c) 2011
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
import unittest

from systemstudio.sslogging import L3

class BuildTestResult(unittest.TestResult):

  separator1 = '=' * 70
  separator2 = '-' * 70

  def __init__(self, logger):
    unittest.TestResult.__init__(self)
    self.logger = logger
    self.warnings = [] # list of all warnings found in this test result

  def getDescription(self, test):
    return test.shortDescription() or str(test)

  def startTest(self, test):
    unittest.TestResult.startTest(self, test)
    self.logger.log(5, L3(self.getDescription(test) + ' ... '), newline=False)

  def addSuccess(self, test):
    unittest.TestResult.addSuccess(self, test)
    self.logger.write(5, 'ok\n')

  def addError(self, test, err):
    unittest.TestResult.addError(self, test, err)
    self.logger.write(5, 'ERROR\n')
    if self.logger.threshold <= 3: # display warning on log level 3 and below
      self.logger.log(1, 'Warning: there was an error in the verification method for test %s: %s' % (test, err[1]))

  def addFailure(self, test, err):
    unittest.TestResult.addFailure(self, test, err)
    self.logger.write(5, 'FAIL\n')
    if self.logger.threshold <= 3: # display warning on log level 3 and below
      #python 2.5
      #self.logger.log(1, 'Warning: %s' % err[1].message)
      #python 2.4 compatible
      self.logger.log(1, 'Warning: %s: %s' % (test, err[1]))
    self.warnings.append(err[1]) # append AssertionError to warning list

  def printErrors(self):
    self.logger.log(5, '')
    self.logger.log(5, self._strErrors())

  def _strErrors(self):
    s = ''
    for flavor, errors in [('ERROR', self.errors), ('FAIL', self.failures)]:
      for test, err in errors:
        s += '%s\n' % self.separator1
        s += '%s: %s\n' % (flavor, self.getDescription(test))
        s += '%s\n' % self.separator2
        s += '%s' % err
    return s

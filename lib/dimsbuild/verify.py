import unittest

from dimsbuild.logging import L3

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
    self.logger.log(4, L3(self.getDescription(test) + ' ... '), newline=False)

  def addSuccess(self, test):
    unittest.TestResult.addSuccess(self, test)
    self.logger.write(4, 'ok\n')

  def addError(self, test, err):
    unittest.TestResult.addError(self, test, err)
    self.logger.write(4, 'ERROR\n')
    if self.logger.threshold <= 3: # display warning on log level 3 and below
      self.logger.log(1, 'Warning: there was an error in one of the verification methods: %s' % err[1])

  def addFailure(self, test, err):
    unittest.TestResult.addFailure(self, test, err)
    self.logger.write(4, 'FAIL\n')
    if self.logger.threshold <= 3: # display warning on log level 3 and below
      self.logger.log(1, 'Warning: %s' % err[1])
    self.warnings.append(err[1]) # append AssertionError to warning list

  def printErrors(self):
    self.logger.log(4, '')
    self.logger.log(4, self._strErrors())
  
  def _strErrors(self):
    s = ''
    for flavor, errors in [('ERROR', self.errors), ('FAIL', self.failures)]:
      for test, err in errors:
        s += '%s\n' % self.separator1
        s += '%s: %s\n' % (flavor, self.getDescription(test))
        s += '%s\n' % self.separator2
        s += '%s' % err
    return s

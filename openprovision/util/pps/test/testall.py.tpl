from openprovision.util import pps
import doctest

for file in pps.path(__file__).dirname.listdir().filter('*.py'):
  doctest.testfile(file, module_relative=False)

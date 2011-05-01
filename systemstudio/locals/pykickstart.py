from systemstudio.locals import LocalsDict, REMOVE

__all__ = ['L_PYKICKSTART']

L_PYKICKSTART = LocalsDict({
  "pykickstart-0": """
from pykickstart.parser import *
try:
  ksdata = KickstartData()
  kshandlers = KickstartHandlers(ksdata)
  parser = KickstartParser(ksdata,kshandlers)
  parser.readKickstart('%(ksfile)s')
except KickstartParseError, e:
  raise KickstartValidationError(e.value)""",
  "pykickstart-1.74": """
from pykickstart.parser  import *
from pykickstart.version import makeVersion
try:
  parser = KickstartParser(makeVersion('%(ksver)s'))
  parser.readKickstart('%(ksfile)s')
except KickstartParseError, e:
  raise KickstartValidationError(e.value)"""
  },)

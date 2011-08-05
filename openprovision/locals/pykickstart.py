from openprovision.locals import LocalsDict, REMOVE

__all__ = ['L_PYKICKSTART']

L_PYKICKSTART = LocalsDict({
  "pykickstart-0": """
from pykickstart.parser import *
# el5 pykickstart doesn't understand el6 kickstart syntax, e.g. end
if self.cvars['base-info']['version'] <= '6':
  try:
    ksdata = KickstartData()
    kshandlers = KickstartHandlers(ksdata)
    parser = KickstartParser(ksdata,kshandlers)
    parser.readKickstart('%(ksfile)s')
  except (KickstartParseError, KickstartValueError), e:
    raise KickstartValidationError(e.value + '\\n' + self.kssource)""",
  "pykickstart-1.74": """
from pykickstart.parser  import *
from pykickstart.version import makeVersion
try:
  parser = KickstartParser(makeVersion('%(ksver)s'))
  parser.readKickstart('%(ksfile)s')
except (KickstartParseError, KickstartValueError), e:
  raise KickstartValidationError(e.value + '\\n' + self.kssource)"""
  },)

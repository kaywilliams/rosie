from systembuilder.locals import LocalsDict

__all__ = ['L_KICKSTART']

try:
  import pykickstart.version as ksversion

  L_KICKSTART = LocalsDict({
    "anaconda-0":           ksversion.RHEL5,
    "anaconda-11.2.0.66-1": ksversion.F7,
    "anaconda-11.3.0.50-2": ksversion.F8,
    "anaconda-11.4.0.82-1": ksversion.F9,
    "anaconda-11.4.1.50-1": ksversion.F10,
  })
except ImportError:
  # until pykickstart is required, simply pass on import error
  L_KICKSTART = LocalsDict({})

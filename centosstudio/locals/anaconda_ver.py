from centosstudio.locals import LocalsDict

__all__ = ['L_ANACONDA_VERSION']

# derive anaconda version from base distribution version
L_ANACONDA_VERSION = LocalsDict({
  "5":   '11.1.2', 
  "6":   '13.21.82',
  "6.2": '13.21.149.1', 
})

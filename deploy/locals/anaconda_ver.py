from deploy.locals import LocalsDict

__all__ = ['L_ANACONDA_VERSION']

# derive anaconda version from base distribution version
L_ANACONDA_VERSION = {
  "el" : LocalsDict({
    "5":   '11.1.2', 
    "6":   '13.21.82',
    "6.2": '13.21.149.1', 
    "6.3": '13.21.176.1',
    "7.0": '19.31.36',
  }),
  "fc" : LocalsDict({
    "19": '19.30.13',
  }),
}

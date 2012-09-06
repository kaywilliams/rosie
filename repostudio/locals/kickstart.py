from repostudio.locals import LocalsDict, REMOVE

__all__ = ['L_KICKSTART_ADDS']

L_KICKSTART_ADDS = LocalsDict({
  "anaconda-0": {
    'version': {
      'test' : "line.startswith('#version')",
      'text' : "\n# version rhel%s" # resolved at runtime
      },
    'packages': {
      'test' :  "line.startswith('%packages')",
      'text' : "\n%packages\n@core",
      },
    },
 "anaconda-13.21": {
    'packages': REMOVE, 
    },
  })

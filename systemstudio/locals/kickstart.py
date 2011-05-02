from systemstudio.locals import LocalsDict, REMOVE

__all__ = ['L_KICKSTART_ADDS']

L_KICKSTART_ADDS = LocalsDict({
  "pykickstart-0": {
    'version': {
      'test' : "line.startswith('#version')",
      'text' : ""  # provided at runtime by the event
      },
    'packages': {
      'test' :  "line.startswith('%packages')",
      'text' : "\n%packages\ngroup core",
      },
    },
 "pykickstart-1.74": {
    'packages': {
      'test' :  "line.startswith('%packages')",
      'text' : "\n%packages\ngroup core\n%end", # introduced trailing %end
      },
    },
  })

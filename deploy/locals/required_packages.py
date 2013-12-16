from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_REQUIRED_PACKAGES']

# additional packages required by anaconda for use during installation
L_REQUIRED_PACKAGES = LocalsDict({
  "anaconda-0": {
    'packages': [ ],
    'groups'  : [ ],
  },
  "anaconda-19.30.13": {
    'packages': ['chrony', 'grub2'],
    'groups'  : [ ],
  },
  "anaconda-19.31.36": {
    # see https://bugzilla.redhat.com/show_bug.cgi?id=1040707
    'packages': ['chrony', 'firewalld', 'grub2'],
    'groups':   ['anaconda-tools'],
  },
})

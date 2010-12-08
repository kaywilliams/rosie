"statfmt.py - computes ls-style formatting for stat().st_mode values"

import stat

TYPE_DIR  = 'd'
TYPE_CHR  = 'c'
TYPE_BLK  = 'b'
TYPE_FIFO = 'f' # guessing on this one
TYPE_LNK  = 'l'
TYPE_SOCK = 's'
TYPE_REG  = '-'

MODE_R = 'r'
MODE_W = 'w'
MODE_X = 'x'
MODE_NONE = '-'

def format(mode):
  t = _format_type(mode)
  u,g,o = _format_permissions(mode)
  return '%s%s%s%s' % (t,u,g,o)

def _format_type(mode):
  # type
  if stat.S_ISREG(mode): # optimize common cases first
    return TYPE_REG
  elif stat.S_ISDIR(mode):
    return TYPE_DIR
  elif stat.S_ISLNK(mode):
    return TYPE_LNK
  # other classes here...
  elif stat.S_ISCHR(mode):
    return TYPE_CHR
  elif stat.S_ISBLK(mode):
    return TYPE_BLK
  elif stat.S_ISFIFO(mode):
    return TYPE_FIFO
  elif stat.S_ISSOCK(mode):
    return TYPE_SOCK
  else:
    raise ValueError("Unknown mode")

def _format_permissions(mode):
  # user perms
  user = \
    ((mode & stat.S_IRUSR) and MODE_R or MODE_NONE) + \
    ((mode & stat.S_IWUSR) and MODE_W or MODE_NONE) + \
    ((mode & stat.S_IXUSR) and MODE_X or MODE_NONE)
  group = \
    ((mode & stat.S_IRGRP) and MODE_R or MODE_NONE) + \
    ((mode & stat.S_IWGRP) and MODE_W or MODE_NONE) + \
    ((mode & stat.S_IXGRP) and MODE_X or MODE_NONE)
  other = \
    ((mode & stat.S_IROTH) and MODE_R or MODE_NONE) + \
    ((mode & stat.S_IWOTH) and MODE_W or MODE_NONE) + \
    ((mode & stat.S_IXOTH) and MODE_X or MODE_NONE)

  return user, group, other

def deformat(s):
  "Transform a formatted string back into a mode"
  t = _deformat_type(s)
  p = _deformat_permissions(s)
  return t|p

def _deformat_type(s):
  type = s[0] # strip off permissions
  if type == TYPE_REG: # optimize common cases first
    return stat.S_IFREG
  elif type == TYPE_DIR:
    return stat.S_IFDIR
  elif type == TYPE_LNK:
    return stat.S_IFLNK
  # other classes here
  elif type == TYPE_CHR:
    return stat.S_IFCHR
  elif type == TYPE_BLK:
    return stat.S_IFBLK
  elif type == TYPE_FIFO:
    return stat.S_IFIFO
  elif type == TYPE_SOCK:
    return stat.S_IFSOCK
  else:
    raise ValueError("Unknown mode")

def _deformat_permissions(s):
  return \
    ( (s[1] == MODE_R and stat.S_IRUSR or 0) | # user
      (s[2] == MODE_W and stat.S_IWUSR or 0) |
      (s[3] == MODE_X and stat.S_IXUSR or 0) |
      (s[4] == MODE_R and stat.S_IRGRP or 0) | # group
      (s[5] == MODE_W and stat.S_IWGRP or 0) |
      (s[6] == MODE_X and stat.S_IXGRP or 0) |
      (s[7] == MODE_R and stat.S_IROTH or 0) | # other
      (s[8] == MODE_W and stat.S_IWOTH or 0) |
      (s[9] == MODE_X and stat.S_IXOTH or 0) )

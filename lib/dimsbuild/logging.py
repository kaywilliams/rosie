import sys

# format of the various printouts
def LEVEL_0_FORMAT(s): return '%s' % s
def LEVEL_1_FORMAT(s): return ' * %s' % s
def LEVEL_2_FORMAT(s): return '   - %s' % s
def LEVEL_3_FORMAT(s): return '     + %s' % s
def LEVEL_4_FORMAT(s): return '       o %s' % s

# convenience for imports/usage
L0 = LEVEL_0_FORMAT
L1 = LEVEL_1_FORMAT
L2 = LEVEL_2_FORMAT
L3 = LEVEL_3_FORMAT
L4 = LEVEL_4_FORMAT

MSG_MAXWIDTH = 75

class BuildLogger:
  def __init__(self, threshold, fo=sys.stdout):
    self.threshold = int(threshold)
    self.fo = fo
  
  def __call__(self, *args, **kwargs):
    self.log(*args, **kwargs)
  
  def test(self, threshold):
    return threshold <= self.threshold
  
  def write(self, level, msg, width=None):
    """ 
    Raw write msg to stdout (trailing newline not appended).  The width
    argument determines how wide the string is.  If it is None, no adjustments
    are applied; if it is a positive integer, the line is padded or truncated
    to match the specified width.
    """
  
    if not self.test(level): return
    
    if width is not None:
      if width < 4:
        raise ValueError("Width must be a positive integer greater than 4 or None")
      diff = len(msg) - width
      if diff > 0:
        msg = msg[:-(diff+4)]
        msg += '... '
      else:
        msg += ' ' * (diff*-1)
    
    self.fo.write(msg)
    self.fo.flush()
  
  def log(self, level, msg, maxwidth=None):
    self.write(level, msg, maxwidth)
    self.write(level, '\n')

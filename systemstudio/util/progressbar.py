#
# Copyright (c) 2012
# System Studio Project. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
"""
progressbar.py

Library for displaying progress bars

Defines a basic status bar class that can be used to draw bars to any file
object, usually the console.

Appearance and content of bars and related statistics is flexible.  Bar layout
is controlled via a tag system described below; additionally, the characters
that represent each individual part of the bar are fully configurable.

Layouts

Bars contain a layout variable which is a string that represents the layout
of the bar on the screen.  It can contain any string character as well as one
or more 'tags', which are indicated using sprintf-style % replacement strings
in the layout.  For example, to use the bar tag, the layout could contain
'%(bar)s'.

A layout can constist of any number of tags and non-tag characters in any
order; tags can be repeated if desired as well.  Although the layout is
usually constant during the process of a bar's lifetime, it can be changed
at any time by modifying the bar's layout variable.

Tags

Tags are the values that are used to replace the variables in the layout,
above.  They can either be callable python objects, in which case the result
of calling the object is used in the bar string, or strings themselves, in
which case no special processing is performed.  Tags are contained inside a
special dictionary so that they can be used in a <string> % <dict> construct
when formatting output.  The tag name in the layout corresponds to the key
inside the mapping dictionary for the tag class in question.  For example,
in the default container, the 'bar' tag refers to the TAG_BAR class, which,
when called, returns a representation of a progress bar computed based on
certain ProgressBar status parameters and local tag variables.

There is an important distinction in the formatting of the final output for
a ProgressBar.  There are essentially two locations where changes can affect
the output - in the layout and in individual tag parameters.  The important
distinction is that the layout affects only the positions and widths of the
various fields of the final result, while the tags themselves only affect
the characters that appear in the tag replacement.  This means, for example,
that you can change the 'condense' property on number tags, but the
ProgressBar that is drawn won't necessarily change in overall size, depending
on the layout (specifically, if the layout limits the size by doing something
like '%(number)5.5s', the output of this tag will always be 5 characters in
length, regardless of the return value of TAG_NUMBER()).

Status objects

Each bar has a status object which reflects the status of a number of
bar variables, including start time, current position, and maximum size.
The status object is intended to be modified at runtime by other functions
and methods in other classes and modules.  As with tags, any change to status
variables will cause the bar to immediately redraw, throttling permitting.

(I'm not really that happy about the distinction between tags and the status
object; realistically the content of the status object could be included as
tags; I may end up making that change in the future.)

Bar Components

A number of variables define the individual components that make up a bar.
The following diagram demonstrates the various parts of the default bar:

         filled   unfilled
        -------- ----------
       [========|----------]
       -        -          -
      lcap   highlight    rcap

Each portion is represented by a single character.  In the default case, lcap
and rcap are '[' and ']', respectively, highlight is '|', filled is '=', and
unfilled is '-'.  By changing the values of these variables, the appearance
of the bar can be customized.  For example, changing the values of lcap and
rcap to '|', highlight to '>', filled to '>', and unfilled to ' ' would
result in the following bar:

         filled   unfilled
        -------- ----------
       |>>>>>>>>>          |
       -        -          -
      lcap   highlight    rcap

Displaying the Bar

ProgressBars are subclasses of the threading.Thread class because they are
actually drawn by an entirely separate thread.  This is necessary due to the
fact that a block somewhere else in the update code could cause the progress
bar to appear to freeze until the block goes away.  By managing bar display
completely independently from its input, the bar can always be kept up to
date on all its values (especially important for tags like TAG_TIME_ELAPSED).

In order to get everything started, call ProgressBar.start().  This creates
the new thread and starts it.  After this point, ProgressBar's run() method
makes repeated calls to draw(), which evaluates the bar's current layout and
writes it to the bar's file object, defaulting to stdout.  Updating the bar's
status in any way, whether it be by changing a tag or one of the status
variables, will cause an immediate redraw.  Furthermore, the bar automatically
redraws itself every 1.0 seconds.

Bar draw()ing can be throttled by setting ProgressBar._throttle to a positive,
nonzero value.  This value determines the maximum number of updates (draw
method calls) that can be made per second.  In general, it is a good idea to
throttle draw() calls if they happen at a very high rate (10+ times per
second) because writing characters to a file object costs a non-zero amount
of time.
"""

import copy
import sys
import threading
import time

from math import floor

layout_default = '%(ratio)8.8s [%(bar)s] %(percent)3.0f%% (%(time-elapsed)s)'
#layout_simple  = '[%(bar)s]'
#layout_nobar   = '%(ratio)8.8s - %(percent)3.0f%% - %(time-elapsed)s'

class ProgressBar(threading.Thread):
  """
  self.layout     : the layout of this bar; can be changed at any time after
                    creation; differences will be reflected upon the next call
                    to draw()
  self.tags       : the tag container with a mapping of tag name to tag objects;
                    used by draw() to perform sprintf replacements in the layout
  self._fo        : the file object to which the progress bar is written.  In
                    most cases, this should be sys.stdout or sys.stderr
  self._throttle  : the number of updates per second allowed by this ProgressBar
  self._last_draw : the time of the last draw() call; used for throttling
  self._event     : the threading.Event object that serves as a condition
                    variable for the ProgressBar, allowing it to draw
                    immediately when changes are detected
  self.status     : the status object containing variables that are changed
                    programatically by callback methods/functions in other
                    classes and modules
  self.finished   : set to True to kill the thread
  """
  def __init__(self, layout=layout_default, tags=None, fo=sys.stdout,
                     position=0.0, size=1.0, throttle=None, **kwargs):
    """
    layout   : set the layout of the bar, defaults to layout_default
    tags     : set the tag container to be used; defaults to tags
    fo       : set the file object; defaults to sys.stdout
    position : the position to start the progress bar at (0 <= position <=
               size)
    size     : the total size of the progress bar (not the size on the screen,
               but the size as in the number of items to show progress on)
    throttle : set the throttle amount of the bar; defaults to None (no
               throttling)
    kwargs   : kwargs are evaluated one at a time, each setting an additional
               tag key,value pair
    """
    self.layout = layout
    self.tags = copy.deepcopy(tags or globals()['tags']) # be thread-safe
    self._fo = fo
    self._throttle = throttle

    self._last_draw = 0 # time of last draw() call

    # create the threading control objects - a lock and a data structure to
    # hold variables
    self._event = threading.Event()
    self.status = Status(self._event)
    self.status.position = position
    self.status.size = size

    self.tags._event = self._event
    self.tags._status = self.status

    # add kwargs to tags list
    for tag, val in kwargs.items():
      self.tags[tag] = val

    threading.Thread.__init__(self)
    self.setDaemon(1)

    self.finished = False

  def __str__(self):
    return self.layout % self.tags

  def start(self):
    "Start drawing the bar"
    t = time.time()
    if not self.status.start_time:
      self.status.start_time = t

    threading.Thread.start(self)

  def run(self):
    "Repeatedly draw() the bar, respecting throttling args"
    while not self.finished:
      self._event.wait(1.0) # update every second, even if nothing changes
      if self._throttle_draw():
        self.draw()
      self._event.clear() # clear the lock
    self.draw()
    if self._fo:
      self._fo.write('\n')
      self._fo.flush()

  def draw(self):
    "Write the bar to self._fo"
    if self._fo:
      self._fo.write('\r' + self.__str__())
      self._fo.flush()
    self._last_draw = time.time()

  def update(self, amount):
    self.status.position = amount

  def join(self):
    self.finished = True
    threading.Thread.join(self)

  finish = join # API difference from previous progressbar

  def _throttle_draw(self):
    "Returns True if ok to draw"
    return not self._throttle or \
           ((time.time() - self._last_draw) >= 1.0/self._throttle)


class Status(object):
  "Status object that contains variable data for ProgressBar objects"
  def __init__(self, event):
    self._position = None
    self._size = None
    self._start_time = None

    self._event = event

  def __set_position(self, pos):
    self._position = self._cap(float(pos), 0.0, self.size)
    self._event.set()

  def __set_size(self, size):
    self._size = self._cap(float(size), 0.0, None)
    self._event.set()

  def __set_start_time(self, time):
    self._start_time = time
    self._event.set()

  def _cap(self, val, minval, maxval):
    if minval: val = max(val, minval)
    if maxval: val = min(val, maxval)
    return val

  position   = property(lambda self: self._position,   __set_position)
  size       = property(lambda self: self._size,       __set_size)
  start_time = property(lambda self: self._start_time, __set_start_time)


#------ TAGS -------#
class TAG(object):
  def update(self, **kwargs):
    for attr, val in kwargs.items():
      if not hasattr(self, attr): raise AttributeError(attr)
      setattr(self, attr, val)

class TAG_TIME(TAG):
  def __init__(self, format='%M:%S'):
    self.format = format

  def __call__(self, status):
    if callable(self.time):
      ftime = self.time(status)
    else:
      ftime = self.time
    return time.strftime(self.format, time.localtime(ftime))

class TAG_TIME_ELAPSED(TAG_TIME):
  def time(self, status):
    return floor(time.time() - status.start_time)

class TAG_TIME_START(TAG_TIME):
  def time(self, status):
    return status.start_time

class TAG_TIME_NOW(TAG_TIME):
  def time(self, status):
    return time.time()

class TAG_PERCENT(TAG):
  def __call__(self, status):
    if status.size:
      return float(100)
    else:
      return float(100*float(status.position)/float(status.size))

class TAG_NUMBER(TAG):
  def __init__(self, condense=False, si=True, ftype=float):
    self.condense = condense
    self.si = si
    self.ftype = ftype

  def __call__(self, status):
    if callable(self.number):
      fnum = self.number(status)
    else:
      fnum = self.number

    if self.ftype == str:
      if self.condense:
        fnum = printf_number(fnum, si=self.si)

    return self.ftype(fnum)

class TAG_CURVALUE(TAG_NUMBER):
  def number(self, status):
    return status.position

class TAG_MAXVALUE(TAG_NUMBER):
  def number(self, status):
    return status.size

class TAG_RATIO(TAG):
  def __init__(self, format='%d', condense=False, si=True, ftype=int):
    self.format = format
    self.condense = condense
    self.si = si
    self.ftype = ftype

  def __call__(self, status):
    fnum = status.position
    fden = status.size

    if self.ftype == str:
      if self.condense:
        fnum = printf_number(fnum, si=self.si)
        fden = printf_number(fden, si=self.si)

    return (self.format+'/'+self.format) % (self.ftype(fnum), self.ftype(fden))

class TAG_BAR(TAG):
  def __init__(self, width=25, unfilled='-', filled='=', highlight='|'):
    self.width     = width
    self.unfilled  = unfilled
    self.filled    = filled
    self.highlight = highlight

  def __call__(self, status):
    # when not at 0 or 100% (include highlight)
    if status.position and status.position != status.size:
      if not status.size:
        len_filled = self.width; len_unfilled = 0
      else:
        len_filled = int(round((self.width - 1) * float(status.position)/float(status.size)))
        len_unfilled = int((self.width - 1) - len_filled)
      return self.filled * len_filled + \
             (self.highlight or self.filled) + \
             self.unfilled * len_unfilled
    # when at 0 or 100% (do not include highlight)
    else:
      if not status.size:
        len_filled = self.width; len_unfilled = 0
      else:
        len_filled = int(round(self.width * float(status.position)/float(status.size)))
        len_unfilled = int(self.width - len_filled)
      return self.filled * len_filled + \
             self.unfilled * len_unfilled

#------ END TAGS ------#


class TagContainer(dict):
  def __getitem__(self, key):
    # self._status must be set
    assert hasattr(self, '_status')
    item = dict.__getitem__(self, key)
    if callable(item):
      return item(self._status)
    else:
      return item

  def __setitem__(self, key, val):
    dict.__setitem__(self, key, val)
    if hasattr(self, 'event'):
      self._event.set()

#------ DEFAULT TAGS ------#
tags = TagContainer()
tags['time-elapsed'] = TAG_TIME_ELAPSED()
tags['time-now']     = TAG_TIME_NOW()
tags['time-start']   = TAG_TIME_START()
tags['bar']          = TAG_BAR()
tags['percent']      = TAG_PERCENT()
tags['curvalue']     = TAG_CURVALUE()
tags['maxvalue']     = TAG_MAXVALUE()
tags['ratio']        = TAG_RATIO()


#------ UTILITY FUNCTIONS ------#
def printf_number(number, si=False, sep=' '):
  order = [' ', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']

  if si: step = 1000.0
  else:  step = 1024.0

  thresh = 999
  depth = 0
  max_depth = len(order) - 1

  # number formatting will be borked for numbers larger than 999 'yotta'
  while number > thresh and depth < max_depth:
    depth += 1
    number = number/step

  if type(number) == type(0) or type(number) == type(0L): # above division didn't$
    format = '%i%s%s'
  elif number < 9.95: # 9.95 to ensure proper formatting with %.1f
    format = '%.1f%s%s'
  else:
    format = '%.0f%s%s'

  return format % (float(number or 0), sep, order[depth])


#----- TESTING ------#
def simulate(bar=None, step=1, sleep=0.05):
  if not bar:
    bar = ProgressBar()
    bar.status.size = 300
  bar.start()

  while bar.status.position < bar.status.size:
    time.sleep(sleep)
    bar.status.position += step


import copy
import optparse
import os
import unittest

from StringIO import StringIO

from dims import pps
from dims import xmllib

from dimsbuild.main import Build

opt_defaults = dict(
  logthresh = 0,
  logfile = None,
  libpath = [],
  sharepath = ['/home/dmusgrave/workspace/dimsbuild/share/dimsbuild'], #!
  #mainconfigpath = None,
  #distropath = './%s.conf' % eventid
  force_modules = [],
  skip_modules = [],
  force_events = [],
  skip_events = [],
  enabled_modules = [],
  disabled_modules = [],
  list_events = False,
  no_validate = True,
)


class TestBuild(Build):
  def __init__(self, conf, *args, **kwargs):
    self.conf = conf
    Build.__init__(self, *args, **kwargs)
  
  def _get_config(self, options):
    return xmllib.config.read(StringIO('<dimsbuild/>')), \
           xmllib.config.read(self.conf)
  

class EventTest(unittest.TestCase):
  def __init__(self, eventid, conf):
    self.eventid = eventid
    self.conf = conf
    
    self.event = None
    unittest.TestCase.__init__(self)
    
    self.options = optparse.Values(defaults=opt_defaults)
    self.parser = None
    
    self.tb = None
    
    self._testMethodDoc = self.__class__.__doc__
  
  def setUp(self):
    self.tb = TestBuild(self.conf, self.options, self.parser)
    self.event = self.tb.dispatch._top.get(self.eventid)
  
  def tearDown(self):
    del self.tb
    del self.event
  
  def clean_all_md(self):
    self.event.METADATA_DIR.rm(recursive=True, force=True)
  def clean_event_md(self, event=None):
    (event or self.event).mddir.rm(recursive=True, force=True)

  def failIfExists(self, path):
    self.failIf(pps.Path(path).exists(), "'%s' exists" % path)
  def failUnlessExists(self, path):
    self.failUnless(pps.Path(path).exists(), "'%s' does not exist " % path)

def main():
  import imp
  
  for event in pps.Path('events').findpaths(mindepth=1, maxdepth=1, type=pps.constants.TYPE_DIR):
    fp = None
    try:
      try:
        fp,p,d = imp.find_module(event.basename, [event.dirname])
      except ImportError:
        continue
      mod = imp.load_module('test-%s' % event.basename, fp, p, d)
    finally:
      fp and fp.close()
    
    mod.main()
    del mod
    

if __name__ == '__main__':
  # test everything
  main()

import unittest

from dims               import pps
from dims.xmllib.config import Element

from test import EventTest

#------ FileDownloadMixin ------#
class FDMTest_Files(EventTest):
  "all files downloaded successfully"
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)
    
    for file in self.event.io.list_output():
      self.failUnlessExists(file) # need to check for virtual?

def fdm_make_suite(eventid, conf):
  suite = unittest.TestSuite()
  suite.addTest(FDMTest_Files(eventid, conf))
  return suite


#------ ImageModifyMixin ------#
import time

starttime = time.time()
files = ['infile', 'infile2', '/tmp/outfile']

class ImageModifyMixinTestCase(EventTest):
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
    self.image_content = None
  
  def setUp(self):
    EventTest.setUp(self)
    self.clean_event_md()
    
    # touch input files
    for file in files:
      ifilename = self.event.config.getroot().file.abspath().dirname/file
      ifilename.touch()
      ifilename.utime((starttime, starttime)) # make sure start times match
    
    # add config entries
    a = {'dest': '/infiles'}
    Element('path', text='/tmp/outfile', parent=self.event.config)
    Element('path', text='infile',  parent=self.event.config, attrs=a)
    Element('path', text='infile2', parent=self.event.config, attrs=a)
  
  def tearDown(self):
    for file in files:
      ifilename = self.event.config.getroot().file.abspath().dirname/file
      ifilename.remove()
  
  def populate_image_content(self):
    if self.image_content is not None: return
    self.event.image.open()
    try:
      self.image_content = self.event.image.list(relative=True)
    finally:
      self.event.image.close()
  
  def check_file_in_image(self, file):
    self.populate_image_content()
    self.failUnless(file.lstrip('/') in self.image_content,
                    "'%s' not in %s" % (file.lstrip('/'), self.image_content))

class IMMTest_Content(ImageModifyMixinTestCase):
  "image content included in final image"
  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)
    
    for dst, src in (self.event.cvars['%s-content' % self.event.id] or {}).items():
      dst = pps.Path(dst)
      self.check_file_in_image(dst)
      for s in src:
        self.check_file_in_image(dst/s.basename)

class IMMTest_ConfigPaths(ImageModifyMixinTestCase):
  "all config-based paths included in final image"
  def __init__(self, eventid, conf, path_xpath=None):
    ImageModifyMixinTestCase.__init__(self, eventid, conf)
    self.path_xpath = path_xpath or 'path'
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    
    for path in self.event.config.xpath(self.path_xpath):
      dest = pps.Path(path.attrib.get('dest', '/'))
      file = dest/pps.Path(path.text).basename
      self.check_file_in_image(file)

def imm_make_suite(eventid, conf, xpath=None):
  suite = unittest.TestSuite()
  suite.addTest(IMMTest_Content(eventid, conf))
  suite.addTest(IMMTest_ConfigPaths(eventid, conf, xpath))
  return suite


#------ BootConfigMixin ------#
class BootConfigMixinTestCase(EventTest):
  def _append_method_arg(self, args):
    if self.event.cvars['web-path']:
      args.append('method=%s/os' % self.event.cvars['web-path'])
  
  def _append_ks_arg(self, args):
    if self.event.cvars['ks-path']:
      args.append('ks=file:%s' % self.event.cvars['ks-file'])
  
  def _append_config_args(self, args):
    if self.event.cvars['boot-args']:
      args.extend(self.cvars['boot-args'].split())
  
  def testArgs(self, image, filename='isolinux.cfg', defaults=True):
    image.open('r')
    try:
      labels = self._get_boot_args(image.list().fnmatch(filename)[0])
      if defaults:
        self._check_boot_args(labels, self.default_args)
      self._check_boot_args(labels, self.event.bootconfig._expand_macros(
        self.event.config.get('boot-config/append-args/text()', '')).split())
    finally:
      image.close()
  
  def _get_boot_args(self, file):
    lines = file.read_lines()
    
    labels = []
    _label = False
    for i in range(0, len(lines)):
      tokens = lines[i].strip().split()
      if not tokens: continue
      if   tokens[0] == 'label': _label = True
      elif tokens[0] == 'append':
        if not _label: continue
        labels.append(tokens[1:])
    
    return labels
  
  def _check_boot_args(self, labels, args):
    for label in labels:
      if label[0] == '-':
        self.failIf(len(label) > 1)
        continue
      else:
        for arg in args:
          self.failUnless(arg in label, "'%s' not in '%s'" % (arg, label))


if __name__ == '__main__':
  eventid = 'product-image'
  runner = unittest.TextTestRunner(verbosity=2)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(IMMTest_Content(eventid, '%s/%s.conf' % (eventid, eventid)))

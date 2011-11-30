#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
from centosstudio.util               import pps
from centosstudio.util.rxml.config import Element

from cstest import decorate
from cstest.core import CoreTestSuite

#------ FileDownloadMixin ------#
class FDMTest_Files:
  "all files downloaded successfully"
  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)

    for file in self.event.io.list_output():
      self.failUnlessExists(file) # need to check for virtual?

def FDMTest_Files(self):
  self._testMethodDoc = "all files downloaded successfully"

  def runTest(): # this test is probably unnecessary, as all events do this now
    self.tb.dispatch.execute(until=self.eventid)

    for file in self.event.io.list_output():
      self.failUnlessExists(file)

  self.runTest = runTest

  return self

def fdm_make_suite(TestCase, distro, version, arch, conf=None):
  suite = CoreTestSuite()
  suite.addTest(FDMTest_Files(TestCase(distro, version, arch, conf)))
  return suite


#------ ImageModifyMixin ------#
class ImageModifyMixinTestCase:
  def __init__(self):
    self.image_content = None

  def setUp(self):
    self.clean_event_md()

    # touch input files
    touch_input_files(self.buildroot)

    # add config entries
    a = {'destdir': '/infiles'}
    Element('files', text='/tmp/outfile', parent=self.event.config)
    Element('files', text='%s/infile' % self.buildroot,  
                     parent=self.event.config, attrs=a)
    Element('files', text='%s/infile2' % self.buildroot,
                     parent=self.event.config, attrs=a)

  def tearDown(self):
    remove_input_files(self.buildroot)

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

def IMMTest_Content(self):
  self._testMethodDoc = "image content included in final image"

  def runTest():
    self.tb.dispatch.execute(until=self.eventid)

    for dst, src in (self.event.cvars['%s-content' % self.event.id] or {}).items():
      dst = pps.path(dst)
      self.check_file_in_image(dst)
      for s in src:
        self.check_file_in_image(dst/s.basename)

  self.runTest = runTest

  return self

def IMMTest_ConfigPaths(self, path_xpath):
  self._testMethodDoc = "all config-based paths included in final image"

  self.path_xpath = path_xpath or 'path'

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)

    for path in self.event.config.xpath(self.path_xpath):
      dest = pps.path(path.attrib.get('destdir', '/'))
      file = dest/pps.path(path.text).basename
      self.check_file_in_image(file)

  self.runTest = runTest

  return self

def imm_make_suite(TestCase, distro, version, arch, conf=None, xpath=None):
  suite = CoreTestSuite()
  suite.addTest(IMMTest_Content(TestCase(distro, version, arch, conf)))
  suite.addTest(IMMTest_ConfigPaths(TestCase(distro, version, arch, conf), xpath))
  return suite


#------ BootConfigMixin ------#
class BootConfigMixinTestCase:
  def _append_method_arg(self, args):
    if self.event.cvars['web-path']:
      args.append('method=%s/os' % self.event.cvars['web-path'])

  def _append_ks_arg(self, args):
    if self.event.cvars['ks-path']:
      args.append('ks=file:%s' % self.event.cvars['ks-path'])

  def _append_config_args(self, args):
    if self.event.cvars['boot-args']:
      args.extend(self.cvars['boot-args'].split())

  def testArgs(self, image, filename='isolinux.cfg', defaults=True):
    image.open('r')
    try:
      labels = self._get_boot_args(image.list().fnmatch(filename)[0])
      if defaults:
        self._check_boot_args(labels, self.default_args)
      self._check_boot_args(labels, 
                      self.event.config.get('boot-args/text()', '').split())
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


# input file creation function
import time

starttime = time.time()
files = ['infile', 'infile2', '/tmp/outfile']

def touch_input_files(dir):
  for file in files:
    ifilename = dir/file
    ifilename.touch()
    ifilename.utime((starttime, starttime)) # make sure start times match

def remove_input_files(dir):
  for file in files:
    (dir/file).remove()

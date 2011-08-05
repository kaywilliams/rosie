#
# Copyright (c) 2011
# Rendition Software, Inc. All rights reserved.
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
import errno
import os

from systemstudio.util import pkgorder
from systemstudio.util import shlib

from systemstudio import splittree

from systemstudio.callback import BuildDepsolveCallback
from systemstudio.event    import Event, CLASS_META
from systemstudio.sslogging  import L1, L2, L3

from systemstudio.modules.shared import ListCompareMixin, BootConfigMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PkgorderEvent', 'IsoEvent'],
  description = 'creates CD/DVD install images',
)

YUMCONF = '''
[main]
cachedir=
gpgcheck=0
reposdir=/
exclude=*debuginfo*

[%s]
name = %s - $basearch
baseurl = file://%s
'''

class PkgorderEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pkgorder',
      parentid = 'all',
      provides = ['pkgorder-file'],
      requires = ['repomd-file', 'os-dir'],
    )

    self.DATA =  {
      'input':     [],
      'output':    []
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.DATA['input'].append(self.cvars['repomd-file'])

    self.pkgorderfile = self.mddir/'pkgorder'
    self.DATA['output'].append(self.pkgorderfile)

  def run(self):
    # delete prior pkgorder file, if exists
    self.io.clean_eventcache(all=True)

    # generate pkgorder
    self.log(1, L1("generating package ordering"))

    # create yum config needed by pkgorder
    cfg = self.TEMP_DIR/'pkgorder'
    repoid = self.distributionid
    cfg.write_lines([ YUMCONF % (self.distributionid, self.distributionid, self.cvars['os-dir']) ])

    # create pkgorder
    pkgtups = pkgorder.order(config=cfg,
                             arch=self.arch,
                             callback=BuildDepsolveCallback(self.logger))

    # cleanup
    cfg.remove()

    # write pkgorder
    pkgorder.write_pkgorder(self.pkgorderfile, pkgtups)

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['pkgorder-file'] = self.pkgorderfile

  def verify_pkgorder_exists(self):
    "verify pkgorder file exists"
    self.verifier.failUnlessExists(self.pkgorderfile)


class IsoEvent(Event, ListCompareMixin, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'iso',
      version = '0.1',
      parentid = 'all',
      provides = ['iso-dir', 'publish-content'],
      requires = ['anaconda-version', 'pkgorder-file', 
                  'boot-config-file', 'treeinfo-file'],
      conditionally_requires = ['srpms-dir', 'ks-path', 'boot-args'],
    )
    ListCompareMixin.__init__(self)
    BootConfigMixin.__init__(self)

    self.lfn = self._delete_isotree
    self.rfn = self._generate_isotree
    self.bfn = self._extend_diffdata

    self.splittrees = self.mddir/'split-trees'

    self.DATA =  {
      'config':    ['.'],
      'variables': ['cvars[\'srpms\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.isodir = self.mddir/'iso'

    self.DATA['input'].extend([self.cvars['pkgorder-file'],
                               self.cvars['treeinfo-file']])

    self.bootconfig.setup(defaults=['method=cdrom'], include_ks=True)

  def run(self):
    oldsets = None

    # remove oldsets if pkgorder file or srpms changed
    if self.diff.input.difference() or \
       self.diff.variables.difference("cvars['srpms']"):
      self.io.clean_eventcache(all=True)
      oldsets = []

    # otherwise get oldsets from metadata file
    if oldsets is None:
      try:
        oldsets = self.diff.config.cfg['set/text()']
      except KeyError:
        oldsets = []

    newsets = self.config.xpath('set/text()', [])

    self.newsets_expanded = []
    for set in newsets:
      self.newsets_expanded.append(splittree.parse_size(set))

    self.compare(oldsets, newsets)

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['iso-dir'] = self.isodir
    try: self.cvars['publish-content'].add(self.isodir)
    except: pass

  def verify_iso_sets(self):
    "each split tree has a corresponding iso with valid size"
    for s in self.config.xpath('set/text()', []):
      splitdir = self.splittrees/s
      isodir   = self.isodir/s
      self.verifier.failUnlessExists(splitdir)
      self.verifier.failUnlessExists(isodir)

      split_sets = [ x.basename for x in splitdir.listdir() ]
      iso_sets   = [ x.basename.replace('.iso', '') for x in isodir.listdir() ]
      diff_set   = set(split_sets).symmetric_difference(iso_sets)
      self.verifier.failIf(diff_set, "iso and split tree sets differ: %s" % diff_set)

      for iso in isodir.listdir():
        isosize = iso.stat().st_size
        self.verifier.failIf(splittree.parse_size(s) < isosize,
                             "size of '%s' (%d) > %s" % (iso, isosize, s))

  def _extend_diffdata(self, set):
    self.DATA['output'].extend([self.splittrees/set, self.isodir/set])

  def _delete_isotree(self, set):
    expanded_set = splittree.parse_size(set)
    if expanded_set in self.newsets_expanded:
      newset = self.newsets[self.newsets_expanded.index(expanded_set)]
      (self.splittrees/set).rename(self.splittrees/newset)
      self.DATA['output'].extend([self.splittrees/set, self.isodir/set])
      if newset in self.r:
        self.r.remove(newset) # don't create iso tree; it already exists

  def _generate_isotree(self, set):
    self.log(1, L1("generating iso tree '%s'" % set))
    (self.isodir/set).mkdirs()
    (self.splittrees/set).mkdirs()

    splitter = splittree.Timber(set, dosrc=self.cvars['srpms-dir'] is not None)
    splitter.name       = self.name
    splitter.u_tree     = self.cvars['os-dir']
    splitter.u_src_tree = self.cvars['srpms-dir']
    splitter.s_tree     = self.splittrees/set
    splitter.product_path = self.cvars['distribution-info']['packagepath']
    splitter.difmt      = self.locals.L_DISCINFO_FORMAT
    splitter.pkgorder   = self.cvars['pkgorder-file']

    self.log(3, L2("splitting trees"))
    self.log(4, L3("computing layout"))
    splitter.compute_layout()
    splitter.cleanup()
    self.log(4, L3("splitting base files"))
    splitter.split_trees()
    # modify boot args on isolinux.cfg file(s)
    for cfg in splitter.s_tree.findpaths(glob='isolinux.cfg'):
      self.bootconfig.modify(cfg)
    self.log(4, L3("splitting rpms"))
    splitter.split_rpms()
    self.log(4, L3("splitting srpms"))
    splitter.split_srpms()

    for i in range(1, splitter.numdiscs + 1):
      iso = '%s-disc%d' % (self.name, i)
      self.log(3, L2("generating '%s/%s.iso'" % (set, iso)))
      if i == 1: # the first disc needs to be made bootable
        isolinux_path = self.splittrees/set/iso/'isolinux/isolinux.bin'
        i_st = isolinux_path.stat()
        bootargs = '-b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table'
      else:
        bootargs = ''
      shlib.execute('mkisofs %s -UJRTV "%s" -o "%s.iso" "%s"' % \
         (bootargs,
          '%s %s disc %d' % \
            (self.name, self.version, i),
          self.isodir/set/iso,
          self.splittrees/set/iso),
        verbose=True)

      if i == 1: # reset mtime on isolinux.bin (mkisofs is so misbehaved in this regard)
        isolinux_path.utime((i_st.st_atime, i_st.st_mtime))

    self.DATA['output'].extend([self.splittrees/set, self.isodir/set])


from ConfigParser import ConfigParser

import os

from dims import filereader
from dims import mkrpm
from dims import pps
from dims import shlib
from dims import sync
from dims import xmltree

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event, EventExit
from dimsbuild.misc      import locals_imerge

P = pps.Path

class RpmBuildEvent(Event):
  def __init__(self, *args, **kwargs):
    Event.__init__(self, *args, **kwargs)
    
    self.build_folder = self.METADATA_DIR/'RPMS'/self.id
    self.srcdir = self.METADATA_DIR/'RPMS'/'rpms-src'/self.id
    
    self.LOCAL_REPO  = self.METADATA_DIR/'RPMS/localrepo'
    self.SOURCES_DIR = self.METADATA_DIR/'RPMS/rpms-src'
    self.LOCAL_RPMS  = self.LOCAL_REPO/'RPMS'
    self.LOCAL_SRPMS = self.LOCAL_REPO/'SRPMS'
    self.RPMS_DEST   = self.SOFTWARE_STORE/self.product
    
    self.cvars['local-rpms'] = self.LOCAL_RPMS
  
  def _clean(self):
    self.remove_output(all=True)
    self.clean_metadata()
    
  def _check(self):
    return self.release == '0' or \
           not self.mdfile.exists() or \
           self.test_diffs()
  
  def add_data(self):
    # input added here 
    # output added in build_rpm, after release number is calculated
    if self.srcdir.exists():
      self.DATA['input'].append(self.srcdir)
  
  def build_rpm(self):
    self.log(0, "building %s rpm" % self.rpmname)
    self.check_release()
    self.log(1, "release number: %s" % self.release)
    self.build()
    self.save_release()
    self.add_output()
  
  def save_release(self):
    rpms_element    = xmltree.uElement('rpms',    parent=self.config.get('/distro'))
    parent_element  = xmltree.uElement(self.id,   parent=rpms_element)
    release_element = xmltree.uElement('release', parent=parent_element)
    
    release_element.text = self.release
    self.config.write(self.config.file)

  def add_output(self):
    self.DATA['output'].extend([
      self.build_folder,
      self.LOCAL_RPMS/ \
           ('%s-%s-%s.%s.rpm' % (self.rpmname, self.version, self.release, self.arch)),
      self.LOCAL_SRPMS/ \
           ('%s-%s-%s.src.rpm' % (self.rpmname, self.version, self.release))
    ])    

  def check_release(self):
    if not self.mdfile.exists() or \
       self.has_changed('input') or \
       self.has_changed('variables') or \
       self.has_changed('config'):
      self.release = str(int(self.release)+1)
  
  def check_rpms(self):
    rpm = self.LOCAL_RPMS/'%s-%s-%s.%s.rpm' % (self.rpmname, self.version,
                                               self.release, self.arch)
    srpm = self.LOCAL_SRPMS/'%s-%s-%s.src.rpm' % (self.rpmname, self.version, self.release)
    if not rpm.exists():
      raise RuntimeError("missing rpm: '%s' at '%s'" % (rpm.basename, rpm))
    if not srpm.exists():
      raise RuntimeError("missing srpm: '%s' at '%s'" % (srpm.basename, srpm))
  
  def test_build(self, default):
    tobuild = self.config.get(['/distro/rpms/%s/@enabled' % self.id,
                               '/distro/rpms/@enabled'], default)
    if tobuild == 'default':
      return default in BOOLEANS_TRUE
    return tobuild in BOOLEANS_TRUE
  
  def generate(self):   pass
  def getiscript(self): return None
  def getpscript(self): return None
  
  def createrepo(self, path=None):
    path = path or self.LOCAL_REPO
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(cwd)
  
  def build(self):
    self.build_folder.mkdirs()
    self.sync_input()    
    self.generate()
    self.write_spec()
    self.write_manifest()
    mkrpm.build(self.build_folder,
                self.LOCAL_REPO,
                keepTemp=True, 
                quiet=(self.logger.threshold < 5))
    (self.build_folder/'dist').rm(recursive=True, force=True)
  
  def register(self, rpmname, description, summary, fileslocals=None, installinfo=None, **kwargs):
    self.rpmname = rpmname
    self.description = description
    self.summary = summary
    
    if fileslocals:
      self.fileslocals = locals_imerge(fileslocals, self.cvars['anaconda-version'])
    else:
      self.fileslocals = None
    
    self.arch      = kwargs.get('arch',      'noarch')
    self.author    = kwargs.get('author',    'dimsbuild')
    self.fullname  = kwargs.get('fullname',  self.fullname)
    self.obsoletes = kwargs.get('obsoletes', None)
    self.provides  = kwargs.get('provides',  None)
    self.release   = kwargs.get('release',   '0')
    self.requires  = kwargs.get('requires',  None)
    self.version   = kwargs.get('version',   self.version)
    
    if installinfo:
      self.installinfo = installinfo
      xpaths = []
      for k,v in self.installinfo.items():
        xpath,_ = v
        if xpath:
          self.setup_sync(self.build_folder/k.lstrip('/'), xpaths=[xpath])
    else:
      self.installinfo = None
  
  def write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'
    if setupcfg.exists(): return # can happen only if setup.cfg is an input file
    
    spec = ConfigParser()
    spec.add_section('pkg_data')
    spec.add_section('bdist_rpm')
    
    spec.set('pkg_data', 'name',             self.rpmname)
    spec.set('pkg_data', 'long_description', self.description)
    spec.set('pkg_data', 'description',      self.summary)
    
    spec.set('pkg_data', 'author',   self.author)
    spec.set('pkg_data', 'version',  self.version)
    
    spec.set('bdist_rpm', 'force_arch',        self.arch)
    spec.set('bdist_rpm', 'distribution_name', self.fullname)
    
    spec.set('bdist_rpm', 'release', self.release)
    
    if self.provides:  spec.set('bdist_rpm', 'provides',  self.provides)
    if self.requires:  spec.set('bdist_rpm', 'requires',  self.requires)
    if self.obsoletes: spec.set('bdist_rpm', 'obsoletes', self.obsoletes)
    
    iscript = self.getiscript()
    pscript = self.getpscript()
    if iscript: spec.set('bdist_rpm', 'install_script', iscript)
    if pscript: spec.set('bdist_rpm', 'post_install', pscript)
    
    self.__addfiles(spec)
    
    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()    
  
  def write_manifest(self):
    manifest = ['setup.py']
    if self.srcdir.exists():
      manifest.extend(self.srcdir.findpaths(type=pps.constants.TYPE_NOT_DIR))
    manifest.extend( [ x.tokens[len(self.build_folder.tokens):] \
                       for x in self.build_folder.findpaths(type=pps.constants.TYPE_NOT_DIR) ] )    
    filereader.write(manifest, self.build_folder/'MANIFEST')
  
  def __addfiles(self, spec):
    # write the list of files to be installed and where they should be installed
    data_files = self.__getfiles()
    if not data_files:
      return
    
    value = []
    for installdir, files in data_files.items():
      value.append('%s : %s' %(installdir, ', '.join(files)))
    spec.set('pkg_data', 'data_files', '\n\t'.join(value))
          
    # mark files to be installed in '/etc' as config files
    config_files = []
    for installdir in data_files.keys():
      if installdir.startswith('/etc'): # config files
        config_files.extend([ installdir/x.basename for x in data_files[installdir] ])
    if config_files:
      spec.set('bdist_rpm', 'config_files', '\n\t'.join(config_files))
    
    # mark files to be installed in '/usr/share/doc' as doc files
    doc_files = []
    for installdir in data_files.keys():
      if installdir.startswith('/usr/share/doc'):
        doc_files.extend([ installdir/x.basename for x in data_files[installdir] ])
    if doc_files:
      spec.set('bdist_rpm', 'doc_files', '\n\t'.join(doc_files))    
  
  def __getfiles(self):
    sources = {}
    if self.srcdir.exists():
      for file in self.srcdir.findpaths(type=pps.constants.TYPE_NOT_DIR):
        dir = file.tokens[len(self.srcdir.tokens):].dirname
        if not dir.isabs():          dir = P('/'+dir)
        if not sources.has_key(dir): sources[dir] = []
        sources[dir].append(file)
    if self.installinfo:
      for k,v in self.installinfo.items():
        dir = self.build_folder/k
        k = P(k)
        if dir.exists():
          files = [ k/x.tokens[len(dir.tokens):] for x in \
                    dir.findpaths(type=pps.constants.TYPE_NOT_DIR) ]
        else:
          files = []
        
        if files:        
          installpath = P(v[1])
          if sources.has_key(installpath):
            sources[installpath].extend(files)
          else:
            sources[installpath] = files
    if self.fileslocals:
      for fileinfo in self.fileslocals.xpath('//files/file', []):
        i = fileinfo.get('@id')
        l = P(fileinfo.get('location/text()'))
        file = self.build_folder/i
        filename = file.basename
        filedir = file.dirname
        installname = l.basename
        installdir = l.dirname
        if filename != installname:
          newfile = filedir/installname
          file.cp(newfile)
          i = newfile
        if not sources.has_key(installdir): sources[installdir] = []
        sources[installdir].append(i)
    return sources


class ColorMixin:
  def setColors(self, be=False, prefix='0x'):    
    # compute the background and foreground colors to use
    self.distroname, self.distroversion = self._get_distro_info()
    try:
      self.bgcolor, self.textcolor, self.hlcolor = \
                    IMAGE_COLORS[self.distroname][self.distroversion]
    except KeyError:
      self.bgcolor, self.textcolor, self.hlcolor = IMAGE_COLORS['*']['0']

    # if be (big-endian) is True, convert the colors to big-endian
    if be:
      self.bgcolor = self.toBigEndian(self.bgcolor)
      self.textcolor = self.toBigEndian(self.textcolor)
      self.hlcolor = self.toBigEndian(self.hlcolor)

    if prefix != '0x':
      self.bgcolor = self.bgcolor.replace('0x', prefix)
      self.textcolor = self.textcolor.replace('0x', prefix)
      self.hlcolor = self.textcolor.replace('0x', prefix)
    
  def toBigEndian(self, color):
    if color.startswith('0x'):
      color = color[2:]
    color = '%s%s' % ((6-len(color))*'0', color) # prepend zeroes to color
    return '0x%s%s%s' % (color[4:], color[2:4], color[:2])

  def _get_distro_info(self):
    fullname = self.cvars['source-vars']['fullname']    
    version = self.cvars['source-vars']['version']
    return fullname, version
  

#---------- ERRORS -------------#
class OutputInvalidError(IOError): pass

#---------- GLOBAL VARIABLES --------#
# each element for a distro's version, e.g. redhat/5, is a 3-tuple:
# (background color, font color, highlight color). To add an entry,
# look at the rhgb SRPM and copy the values from splash.c.
IMAGE_COLORS = {
  'CentOS': {
    '5.0': ('0x215593', '0xffffff', '0x1e518c'),
  },
  'Fedora Core': {
    '6': ('0x00254d', '0xffffff', '0x002044'),  
  },
  'Fedora': {
    '7': ('0x001b52', '0xffffff', '0x1c2959'),
  },
  'Red Hat Enterprise Linux Server': {
    '5': ('0x781e1d', '0xffffff', '0x581715'),
  },
  '*': {
    '0': ('0x00254d', '0xffffff', '0x002044'),
  }
}

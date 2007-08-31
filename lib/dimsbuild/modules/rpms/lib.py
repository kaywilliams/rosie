from ConfigParser import ConfigParser

import os

from dims import filereader
from dims import mkrpm
from dims import pps
from dims import shlib
from dims import sync
from dims import xmltree

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EventInterface, HookExit

P = pps.Path

#------- INTERFACES --------#
class RpmsInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)

    self.LOCAL_REPO  = self.METADATA_DIR/'RPMS/localrepo'
    self.SOURCES_DIR = self.METADATA_DIR/'RPMS/rpms-src'
    self.LOCAL_RPMS  = self.LOCAL_REPO/'RPMS'
    self.LOCAL_SRPMS = self.LOCAL_REPO/'SRPMS'
    self.RPMS_DEST   = self.SOFTWARE_STORE/self.product
    
    self.sharepath = self._base.sharepath

    self.cvars['local-rpms'] = self.LOCAL_RPMS

  def createrepo(self, path=None):
    path = path or self.LOCAL_REPO
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(cwd)

  def addRpm(self, path):
    sync.sync(path, self.LOCAL_REPO) #! fix me
  
  def buildRpm(self, path, rpm_output, changelog=None, logger='rpmbuild',
               createrepo=False, quiet=True):

    mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
                keepTemp=True, createrepo=createrepo,
                quiet=quiet)
    
    # need to delete the dist folder, because the RPMS have been copied
    # already to wherever they need to be.
    (path/'dist').rm(recursive=True, force=True)
    

#------ MIXINS ------#
class ColorMixin:
  def __init__(self): pass

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
    fullname = self.interface.cvars['source-vars']['fullname']    
    version = self.interface.cvars['source-vars']['version']
    return fullname, version


class RpmBuildHook:
  def __init__(self,
               interface,
               data,
               id,
               rpmname,
               version=None,
               arch='noarch',
               summary=None,
               description=None,
               provides=None,
               requires=None,
               obsoletes=None,          
               installinfo={},
               default='True',
               package_type=None,
               condrequires=None):
    """ 
    @param interface   : the interface object for this hook
    @param data        : the diff metadata struct
    @param id          : the id of the hook's event
    @param default     : the value of the enabled attribute
                         if it is 'default'

    RPM spec file related parameters -    
    @param rpmname     : the name of the rpm to build
    @param version     : the version of this RPM
    @param arch        : the architecture for the RPM    
    @param summary     : the summary for the RPM
    @param description : the description of the RPM    
    @param provides    : the items this RPM provides
    @param requires    : the items this RPM requires
    @param obsoletes   : the items this RPM obsoletes

    comps.xml related parameters - 
    @param package_type: the type of the package: mandatory,
                         conditional etc.
    @param condrequires: the package this package conditionally
                         requires

    path element related parameters -
    @param installinfo : the xpath queries to install directory
                         mappings    
    """
    self.interface = interface
    
    self.id      = id
    self.default = default
    
    # spec file information
    self.arch        = arch
    self.author      = 'dimsbuild'
    self.description = description
    self.obsoletes   = obsoletes
    self.provides    = provides
    self.requires    = requires
    self.release     = None # filled in in run()
    self.rpmname     = rpmname
    self.summary     = summary
    self.version     = version or self.interface.version

    # comps.xml information
    self.condrequires = condrequires
    self.package_type = package_type or 'mandatory'    

    # build information
    self.build_folder = self.interface.METADATA_DIR/'RPMS'/self.id
    self.autoconf = P(self.interface.config.file).dirname/'distro.conf.auto'
    
    # input files
    self.installinfo = installinfo

    self.DATA = data
    self.mdfile = self.interface.METADATA_DIR/'RPMS/%s.md' % self.id

  def setup(self):
    # add the directory (if exists) to which other events add files to
    # that are to be installed by this RPM.
    rpmssrc = self.interface.SOURCES_DIR/self.id
    if rpmssrc.exists():
      self.DATA['input'].append(rpmssrc)

    # add output files
    self.DATA['output'].extend([
      self.build_folder,
      self.interface.LOCAL_RPMS/ \
           ('%s-%s-%s.%s.rpm' % (self.rpmname, self.version, self.release, self.arch)),
      self.interface.LOCAL_SRPMS/ \
           ('%s-%s-%s.src.rpm' % (self.rpmname, self.version, self.release))
    ])
      
    self.interface.setup_diff(self.mdfile, self.DATA)

    if self.installinfo:
      xpaths = []
      for k,v in self.installinfo.items():
        xpath,_ = v
        if xpath is not None:
          xpaths.append((xpath,
                         self.build_folder/k.lstrip('/')))
      self.interface.setup_sync(xpaths=xpaths)

  def clean(self):
    self.interface.log(0, "cleaning %s event" % self.id)
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
    
  def check(self):
    return not self.mdfile.exists() or \
           not self.autoconf.exists() or \
           self.interface.test_diffs()
  
  def run(self):
    # ... delete older rpms ...
    self.interface.remove_output(all=True)
    
    # only generate RPM if test_build() returns true
    if not self.test_build():
      return
        
    self.interface.log(0, "building %s rpm" % self.rpmname)

    # compute the release number ...
    self.set_release()
    self.interface.log(1, "rpm release number: %s" % self.release)

    # ... make sure that the build folder exists ...
    self.build_folder.mkdirs()
    
    # ... sync any input files ...
    if self.installinfo:
      self.interface.sync_input()

    # ... generate additional files, if required ...
    self.generate()

    # ... write setup.cfg ...
    self.write_spec()

    # ... write MANIFEST ...
    self.write_manifest()    

    # ... build the RPM ...
    self.interface.buildRpm(self.build_folder, self.interface.LOCAL_REPO,
                            quiet=(self.interface.logthresh < 5))

    # ... test the output's validity ...
    if not self.output_valid():
      raise OutputInvalidError("'%s' output invalid" % self.rpmname)

    # ... update the release number ...
    self.write_autoconf(self.release)
    
    # ... finally, write the metadata file.
    self.interface.cvars['custom-rpms-built'] = True

  def apply(self):
    self.interface.write_metadata()
    
    if not self.test_build():
      return
    release = self.read_autoconf() or '1'
    rpm = self.interface.LOCAL_RPMS/ \
               ('%s-%s-%s.%s.rpm' % (self.rpmname,
                                     self.version,
                                     release,
                                     self.arch))
    srpm = self.interface.LOCAL_SRPMS/ \
                ('%s-%s-%s.src.rpm' % (self.rpmname,
                                       self.version,
                                       release))
    if not rpm.exists():
      raise RuntimeError("missing rpm: %s" % rpm.basename)
    if not srpm.exists():
      raise RuntimeError("missing srpm: %s" % srpm.basename)
      
    if not self.interface.cvars['custom-rpms-info']:
      self.interface.cvars['custom-rpms-info'] = []
      
    self.interface.cvars['custom-rpms-info'].append((self.rpmname,
                                                     self.package_type,
                                                     self.condrequires,
                                                     self.obsoletes))
    
  def test_build(self):
    tobuild = self.interface.config.get('/distro/rpms/%s/@enabled' % self.id,
                   self.interface.config.get('/distro/rpms/@enabled', self.default))
    if tobuild == 'default': tobuild = self.default
    return tobuild in BOOLEANS_TRUE

  def generate(self):
    pass
  
  def output_valid(self):
    return True
  
  def write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'
    if setupcfg.exists(): return # can happen only if setup.cfg is an input file

    spec = ConfigParser()    
    spec.add_section('pkg_data')
    spec.add_section('bdist_rpm')
    
    spec.set('pkg_data', 'name',             self.rpmname)
    spec.set('pkg_data', 'version',          self.version)
    spec.set('pkg_data', 'long_description', self.description)
    spec.set('pkg_data', 'description',      self.summary)
    spec.set('pkg_data', 'author',           self.author)
    
    spec.set('bdist_rpm', 'distribution_name', self.interface.fullname)    
    spec.set('bdist_rpm', 'force_arch',        self.arch)
    spec.set('bdist_rpm', 'release',           self.release)    

    for tag in ['obsoletes', 'provides', 'requires']:
      value = getattr(self, tag)
      if value:
        spec.set('bdist_rpm', tag, value)

    for tag in ['install_script', 'post_install']:
      attr = '_get_%s' %tag
      if hasattr(self, attr):
        value = getattr(self, attr)()
        if value is not None:
          spec.set('bdist_rpm', tag, value)

    self._add_files_info(spec)
    
    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def write_manifest(self):
    manifest = ['setup.py'] # setup.py is created by mkrpm.RpmBuilder
    srcdir = self.interface.SOURCES_DIR/self.id
    if srcdir.exists():
      manifest.extend(srcdir.findpaths(type=pps.constants.TYPE_NOT_DIR))
    if self.build_folder.exists():
      manifest.extend(
        [ x.tokens[len(self.build_folder.tokens):] for x in \
          self.build_folder.findpaths(type=pps.constants.TYPE_NOT_DIR) ] )
    filereader.write(manifest, self.build_folder/'MANIFEST')

  def set_release(self):
    if self.autoconf.exists():
      bumpcheck = False
      self.release = self.read_autoconf()

      if not self.release:
        self.release = '1'
        bumpcheck = True
      elif not self.mdfile.exists():
        # missing .md file
        bumpcheck = True
      else:
        for dtype in ['input', 'variables', 'config']:
          if self.interface.handlers.has_key(dtype) and \
                 self.interface.has_changed(dtype):
            bumpcheck = True
            break

      if bumpcheck:
        if self.interface.cvars['auto-bump-release']:
          self.release = str(int(self.release or '1') + 1)
        else:
          self.interface.log(0, "Current release number is %s" % self.release)
          ans = None
          while not ans or (ans and ans[0] not in 'ice'):
            self.interface._base.log.write(0, "i)ncrement, c)ontinue, e)xit: ")
            ans = raw_input().lower()
          if ans[0] == 'i':
            self.release = str(int(self.release) + 1)
          elif ans[0] == 'e':
            raise HookExit
          else:
            pass # nothing to do
    else:
      # missing .auto file
      if self.interface.cvars['auto-bump-release']:
        self.release = '1'
      else:
        self.interface.log(0, "The distro.conf.auto file is missing")
        ans = None
        while not ans or (ans and ans[0] not in 'se'):
          self.interface._base.log.write(0,"s)tart at 1, e)xit: ")
          ans = raw_input().lower()
        if ans[0] == 's':
          self.release = '1'
        else:
          raise HookExit

  def read_autoconf(self):
    if self.autoconf.exists():
      root = xmltree.read(self.autoconf)
      release = root.get('//distro-auto/%s/release/text()' % self.id, None)
      return release
    return None

  def write_autoconf(self, release):
    if self.autoconf.exists():
      root = xmltree.read(self.autoconf)
      package = root.get('//distro-auto/%s' %self.id, None)
      if package is None:
        package = xmltree.Element(self.id, parent=root)
        
      r = package.get('release', None)
      if r is None:
        r = xmltree.Element('release', parent=package)            
      r.text = release
    else:
      root = xmltree.Element('distro-auto')
      package = xmltree.Element(self.id, parent=root)
      xmltree.Element('release', parent=package, text=release)
    
    root.write(self.autoconf)

  def _add_files_info(self, spec):
    # write the list of files to be installed and where they should be installed
    data_files = self._get_data_files()
    if not data_files: return
    
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

  def _get_data_files(self):
    srcdir = self.interface.SOURCES_DIR/self.id
    sources = {}          
    if srcdir.exists():
      for file in srcdir.findpaths(type=pps.constants.TYPE_NOT_DIR):
        dir = file.dirname
        if not dir.isabs(): dir = P('/'+dir)
        if not sources.has_key(dir):
          sources[dir] = []
        sources[dir].append(file)

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
    
    return sources

  def _get_install_script(self): return None    
  def _get_post_install(self):   return None


#---------- ERRORS -------------#
class OutputInvalidError(IOError):
  pass


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

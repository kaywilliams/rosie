from ConfigParser import ConfigParser
from os.path      import exists, join

import fcntl
import os
import rpm
import socket
import struct

from dims import filereader
from dims import mkrpm
from dims import shlib
from dims import xmltree

from dims.osutils import *
from dims.sync    import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EventInterface
from dimsbuild.interface import DiffMixin

#------ MIXINS ------#
class ColorMixin:
  def __init__(self): pass

  def setColors(self, be=False, prefix='0x'):    
    # compute the background and foreground colors to use
    self.distroname, self.distroversion = self._get_distro_info()
    try:
      self.bgcolor, self.textcolor, self.hlcolor = IMAGE_COLORS[self.distroname][self.distroversion]
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

#---------- INTERFACES -----------#
class RpmsInterface(EventInterface):
  def __init__(self, base):
    self.LOCAL_REPO = join(base.METADATA_DIR, 'localrepo/')
    self.sharepath = base.sharepath
    
    EventInterface.__init__(self, base)

  def getSourcesDirectory(self):
    return join(self.METADATA_DIR, 'rpms-src')

  def addRpm(self, path):
    sync(path, self.LOCAL_REPO)
  
  def createrepo(self, path=None):
    path = path or self.LOCAL_REPO
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(cwd)

  def buildRpm(self, path, rpm_output, changelog=None, logger='rpmbuild',
               createrepo=False, quiet=True):

    mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
                keepTemp=True, createrepo=createrepo,
                quiet=quiet)
    
    # need to delete the dist folder, because the RPMS have been copied
    # already to wherever they need to be. 
    rm(join(path, 'dist'), recursive=True, force=True)

  def getIpAddress(self, ifname='eth0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                        0x8915, # SIOCGIFADDR
                                        struct.pack('256s', ifname[:15]))[20:24])  


#---------- HANDLERS -------------#
class RpmsHandler(DiffMixin):
  def __init__(self, interface, data, id, rpmname,
               summary=None, description=None, installinfo={}):

    if len(data['output']) > 1:
      raise Exception, "only one item should be specified in data['output']"
        
    self.interface = interface

    # self.<k> = self.interface.<v>
    for k,v in [('config',   'config'),   ('fullname',       'fullname'),
                ('arch',     'basearch'), ('software_store', 'SOFTWARE_STORE'),
                ('fullname', 'fullname'), ('product',        'product'),
                ('version',  'version'),  ('metadata',       'METADATA_DIR'),
                ('log',      'log'),      ('sharepath',      'sharepath')]:
      setattr(self, k, getattr(self.interface, v))

    self.id = id
    self.rpmname = rpmname
    self.summary = summary
    self.description = description
    self.author = 'dimsbuild'

    self.output_location = join(self.metadata, self.id)
    self.autoconf = join(dirname(self.config.file), 'distro.conf.auto')

    self.installinfo = installinfo
    
    DiffMixin.__init__(self, join(self.metadata, '%s.md' % self.id), data)

  def setup(self):
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)
    
    rpmssrc = join(self.interface.getSourcesDirectory(), self.id)
    if exists(rpmssrc):      
      self.addInput(self.interface.expand(rpmssrc))
    for k,v in self.installinfo.items():
      xquery,_ = v
      if xquery is not None:
        self.addInput(self.interface.expand(self.interface.config.xpath(xquery, [])))
    
  def force(self):
    self._clean()
    
  def check(self):
    if self._test_build():
      if self.test_diffs(): self._clean(); return True
      else: return False
    else:
      self._clean(); return False
  
  def run(self):
    self.log(0, "building %s rpm" % self.rpmname)

    # sync input files....
    self._copy()

    # ....generate additional files, if required....
    self._generate()

    # ....write setup.cfg....
    self._write_spec()

    # ....write MANIFEST....
    self._write_manifest()    

    # ....finally build the RPM....
    self.interface.buildRpm(self.output_location, self.interface.LOCAL_REPO,
                            quiet=(self.interface.logthresh < 4))
    if not self._valid():
      raise OutputInvalidError("'%s' output invalid" % self.rpmname)

    self.addOutput(self.output_location)
    self.addOutput(join(self.interface.LOCAL_REPO, 'RPMS',
                        '%s*[!Ss][!Rr][!Cc].[Rr][Pp][Mm]' % self.rpmname))
    self.addOutput(join(self.interface.LOCAL_REPO, 'SRPMS',
                        '%s*[Ss][Rr][Cc].[Rr][Pp][Mm]' % self.rpmname))
    self.interface.expand(self.data['output'])

    # ....but wait! Write the metadata file too.
    self.write_metadata()    

  def apply(self, type='mandatory', requires=None):
    missingrpms = [ x for x in self._find_rpms() if not exists(x) ]

    if len(missingrpms) != 0:
      if self._test_build() and not self.interface.isSkipped(self.id):
        raise RuntimeError("missing rpm(s): %s" % ', '.join(missingrpms))
      else:
        return # the rpm hasn't been created, therefore nothing else to do here

    # add rpms to the included-packages control var, so that they are
    # added to the comps.xml
    if not self.interface.cvars['included-packages']:
      self.interface.cvars['included-packages'] = []
    self.interface.cvars['included-packages'].append((self.rpmname, type, requires))

    obsoletes = self._get_obsoletes()
    if obsoletes is not None:
      if not self.interface.cvars['excluded-packages']:
        self.interface.cvars['excluded-packages'] = []
      self.interface.cvars['excluded-packages'].extend(obsoletes.split())

  def _clean(self):
    for rpm in self._find_rpms():
      self.removeOutput(rpm)
      rm(rpm, force=True)
    rm(self.output_location, recursive=True, force=True)
    rm(self.mdfile, force=True)
    self.clean_metadata()

    mkdir(self.output_location, parent=True)    

  def _copy(self):
    for k,v in self.installinfo.items():
      xquery,_ = v
      if xquery is not None:
        for file in self.interface.config.xpath(xquery, []):
          dest = join(self.output_location, k)
          if not exists(dest):
            mkdir(dest, parent=True)
          sync(file, dest)
    
  def _test_build(self):
    return self.config.get('/distro/rpms/%s/create/text()' % self.id, 'True') in BOOLEANS_TRUE

  def _find_rpms(self, prefix=True):
    v,r,a = self._read_autoconf()
    rpm = join('RPMS', '%s-%s-%s.%s.rpm' %(self.rpmname, v, r, a))
    srpm = join('SRPMS', '%s-%s-%s.src.rpm' %(self.rpmname, v, r))    

    if prefix:
      rpm = join(self.interface.LOCAL_REPO, rpm)
      srpm = join(self.interface.LOCAL_REPO, srpm)

    return [rpm, srpm]
  
  def _write_spec(self):
    setupcfg = join(self.output_location, 'setup.cfg')
    if exists(setupcfg): return # can happen only if setup.cfg is an input file
    
    version, release, arch = self._read_autoconf()

    spec = ConfigParser()    
    spec.add_section('pkg_data')
    spec.add_section('bdist_rpm')
    
    spec.set('pkg_data', 'name',             self.rpmname)
    spec.set('pkg_data', 'version',          version)
    spec.set('pkg_data', 'long_description', self.description)
    spec.set('pkg_data', 'description',      self.summary)
    spec.set('pkg_data', 'author',           self.author)
    
    spec.set('bdist_rpm', 'distribution_name', self.fullname)    
    spec.set('bdist_rpm', 'force_arch',        arch)
    
    for tag in ['install_script', 'obsoletes', 'post_install', 'provides', 'requires']:
      attr = '_get_%s' %tag
      if hasattr(self, attr):
        value = getattr(self, attr)()
        if value is not None:
          spec.set('bdist_rpm', tag, value)
    
    release = str(int(release) + 1)
    spec.set('bdist_rpm', 'release',    release)
    self.log(1, "release number: %s" % release)
    self._write_autoconf(release=release)

    self._add_files_info(spec)
    
    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def _add_files_info(self, spec):
    # write the list of files to be installed and where they should be installed
    data_files = self._get_data_files()
    if data_files:
      value = []
      for installdir, files in data_files.items():
        value.append('%s : %s' %(installdir, ', '.join(files)))
      spec.set('pkg_data', 'data_files', '\n\t'.join(value))
      
    
    # mark files to be installed in '/etc' as config files
    config_files = []
    for installdir in data_files.keys():
      if installdir.startswith('/etc'): # config files
        config_files.extend([ join(installdir, basename(x)) for x in data_files[installdir] ])
    if config_files:
      spec.set('bdist_rpm', 'config_files', '\n\t'.join(config_files))

    # mark files to be installed in '/usr/share/doc' as doc files
    doc_files = []
    for installdir in data_files.keys():
      if installdir.startswith('/usr/share/doc'):
        doc_files.extend([ join(installdir, basename(x)) for x in data_files[installdir] ])
    if doc_files:
      spec.set('bdist_rpm', 'doc_files', '\n\t'.join(doc_files))    

  def _write_manifest(self):
    manifest = ['setup.py'] # setup.py is created by mkrpm.RpmBuilder
    srcdir = join(self.interface.getSourcesDirectory(), self.id)
    if exists(srcdir):
      manifest.extend(find(srcdir, type=TYPE_FILE|TYPE_LINK, prefix=True))
    if exists(self.output_location):
      manifest.extend(find(self.output_location, type=TYPE_FILE|TYPE_LINK, prefix=False))
    filereader.write(manifest, join(self.output_location, 'MANIFEST'))          

  def _read_autoconf(self):
    if exists(self.autoconf):
      root = xmltree.read(self.autoconf)
      package = root.get('//distro-auto/%s' %self.id, None)
      if package is not None:
        v = package.get('version/text()', self.version)
        r = package.get('release/text()', '0')
        a = package.get('arch/text()', self._get_force_arch())
        return v,r,a
    return self.version, '0', self._get_force_arch()

  def _write_autoconf(self, version=None, release=None, arch=None):
    if exists(self.autoconf):
      root = xmltree.read(self.autoconf)
      package = root.get('//distro-auto/%s' %self.id, None)
      if package is None: package = xmltree.Element(self.id, parent=root)

      if version is not None:
        v = package.get('version', None)
        if v is None: v = xmltree.Element('version', parent=package)
        v.text = version

      if release is not None:
        r = package.get('release', None)
        if r is None: r = xmltree.Element('release', parent=package)
        r.text = release
        
      if arch is not None:
        a = package.get('arch', None)
        if a is None: a = xmltree.Element('arch', parent=package)
        a.text = arch
    else:
      root = xmltree.Element('distro-auto')
      package = xmltree.Element(self.id, parent=root)
      if version is not None:
        v = xmltree.Element('version', parent=package, text=version)
      if release is not None:
        r = xmltree.Element('release', parent=package, text=release)
      if arch is not None:
        a = xmltree.Element('arch', parent=package, text=arch)
    
    root.write(self.autoconf)

  def _get_data_files(self):
    srcdir = join(self.interface.getSourcesDirectory(), self.id)
    sources = {}          
    if exists(srcdir):
      for file in find(srcdir, type=TYPE_FILE|TYPE_LINK, prefix=False):
        dir = dirname(file)
        if not dir.startswith('/'): dir = '/' + dir
        if not sources.has_key(dir):
          sources[dir] = []
        sources[dir].append(join(srcdir, file))
    for k,v in self.installinfo.items():
      dir = join(self.output_location, k)
      if exists(dir):
        files = [ join(k,x) for x in os.listdir(dir) ]
      else:
        files = []

      if files:        
        installpath = v[1]
        if sources.has_key(installpath):
          sources[installpath].extend(files)
        else:
          sources[installpath] = files
    return sources

  def _generate(self): pass
  
  def _get_force_arch(self):     return 'noarch'

  def _get_install_script(self): return None    
  def _get_obsoletes(self):      return None  
  def _get_post_install(self):   return None
  def _get_provides(self):       return None
  def _get_requires(self):       return None
  
  def _valid(self):              return True

class OutputInvalidError(IOError): pass

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

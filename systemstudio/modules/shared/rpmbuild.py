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
from ConfigParser import ConfigParser

import colorsys
import re

from systemstudio.util import mkrpm
from systemstudio.util import pps
from systemstudio.util import rxml

from systemstudio.errors    import SystemStudioError
from systemstudio.event     import Event
from systemstudio.sslogging   import L1

__all__ = ['RpmBuildMixin', 'Trigger', 'TriggerContainer']

VER_X_REGEX = re.compile('[^0-9]*([0-9]+).*')
GPGKEY_NAME = 'RPM-GPG-KEY-systemstudio'

class RpmBuildMixin:
  def __init__(self, *args, **kwargs):
    self.rpm = RpmBuildObject(self, *args,**kwargs)

  def check(self):
    return self.rpm.release == '0' or \
           not self.rpm.autofile.exists() or \
           self.diff.test_diffs()

  def setup(self):
    self.rpm.setup_build()

  def run(self):
    self.io.clean_eventcache(all=True)

    R = self.rpm

    R.check_release()

    R.build_folder.mkdirs()
    self.generate()
    R.write_spec()
    R.write_manifest()

    self.log(1, L1("building %s-%s-%s.%s.rpm" % \
                   (R.name, R.version, R.release, R.arch)))

    try:
      mkrpm.build(R.build_folder, self.mddir, createrepo=False,
                  bdist_base=R.bdist_base, rpm_base=R.rpm_base,
                  dist_dir=R.dist_dir, keep_source=True,
                  quiet=(self.logger.threshold < 5))
    except mkrpm.rpmbuild.RpmBuilderException, e:
      raise RpmBuildFailedException(message=str(e))

    self.log(4, L1("signing %s-%s-%s.%s.rpm" % \
                   (R.name, R.version, R.release, R.arch)))
    R.sign()

    R.save_release()
    self.DATA['output'].append(R.rpm_path)
    self.DATA['output'].append(R.srpm_path)
    self.DATA['output'].append(self.rpm.build_folder)

  def apply(self):
    self.io.clean_eventcache()

    R = self.rpm

    rpmbuild_data = {}

    rpmbuild_data['packagereq-default']  = R.packagereq_default
    rpmbuild_data['packagereq-requires'] = R.packagereq_requires
    rpmbuild_data['packagereq-type']     = R.packagereq_type

    rpmbuild_data['rpm-name']      = R.name
    rpmbuild_data['rpm-obsoletes'] = R.obsoletes
    rpmbuild_data['rpm-provides']  = R.provides
    rpmbuild_data['rpm-requires']  = R.requires

    rpmbuild_data['rpm-path']  = R.rpm_path
    rpmbuild_data['srpm-path'] = R.srpm_path

    self.cvars['rpmbuild-data'][self.id] = rpmbuild_data

  def verify_rpm_exists(self):
    "rpm exists"
    self.verifier.failUnlessExists(self.rpm.rpm_path)

  def verify_srpm_exists(self):
    "srpm exists"
    self.verifier.failUnlessExists(self.rpm.srpm_path)

  #----------- OPTIONAL METHODS --------#
  def generate(self):
    pass

  # determine what files are ghost
  def get_ghost_files(self): return None

  # rpm scripts
  def get_build(self):        return None
  def get_clean(self):        return None
  def get_install(self):      return None
  def get_post(self):         return None
  def get_postun(self):       return None
  def get_pre(self):          return None
  def get_prep(self):         return None
  def get_preun(self):        return None
  def get_verifyscript(self): return None

  # trigger scripts
  def get_triggers(self):     return None


class RpmBuildObject:
  def __init__(self, ptr, name, desc, summary, license=None,
               provides=None, obsoletes=None, requires=None,
               packagereq_type='mandatory', packagereq_default=None,
               packagereq_requires=None):
    self.ptr = ptr

    self.desc    = desc
    self.name    = name
    self.summary = summary
    self.license = license

    self.obsoletes = obsoletes or []
    self.requires  = requires  or []
    self.provides  = provides  or []

    if not self.ptr.config.getbool('@use-default-obsoletes', 'True'):
      self.obsoletes = []

    self.packagereq_type     = packagereq_type
    self.packagereq_default  = packagereq_default
    self.packagereq_requires = packagereq_requires

    self.autofile = self.ptr._config.file + '.dat'

    # RPM build variables
    self.build_folder  = self.ptr.mddir / 'build'
    self.bdist_base    = self.build_folder / 'rpm-base'
    self.rpm_base      = self.build_folder / 'rpm'
    self.dist_dir      = self.build_folder / 'dist'
    self.source_folder = self.build_folder / 'source'

  #------------- PROPERTIES --------------#
  @property
  def rpm_path(self):
    return self.ptr.mddir/'RPMS/%s-%s-%s.%s.rpm' % \
             (self.name, self.version, self.release, self.arch)

  @property
  def srpm_path(self):
    return self.ptr.mddir/'SRPMS/%s-%s-%s.src.rpm' % \
           (self.name, self.version, self.release)

  @property
  def data_files(self):
    data_files = {}
    for item in self.source_folder.findpaths(type=pps.constants.TYPE_DIR,
                                             mindepth=1):
      files = item.findpaths(type=pps.constants.TYPE_NOT_DIR,
                             mindepth=1, maxdepth=1)
      if files:
        data_files.setdefault('/' / item.relpathfrom(self.source_folder), []).extend(files)
    return data_files

  #--------- RPM BUILD HELPER METHODS ---------#
  def setup_build(self, **kwargs):
    if self.autofile.exists():
      self.release = rxml.tree.read(self.autofile).get(
       '/distribution/rpms/%s/release/text()' %
       (self.ptr.id), '0')
    else:
      self.release = '0'

    self.obsoletes.extend(self.ptr.config.xpath('obsoletes/text()', []))
    self.obsoletes.extend(kwargs.get('obsoletes', []))

    self.provides.extend([ x for x in self.obsoletes ])
    self.requires.extend(self.ptr.config.xpath('provides/text()', []))
    self.provides.extend(kwargs.get('provides', []))

    self.requires.extend(self.ptr.config.xpath('requires/text()', []))
    self.requires.extend(kwargs.get('requires', []))

    self.ptr.diff.setup(self.ptr.DATA)

    self.arch     = kwargs.get('arch',     'noarch')
    self.author   = kwargs.get('author',   'systemstudio')
    self.fullname = kwargs.get('fullname', self.ptr.fullname)
    if kwargs.has_key('version'):
      self.version = kwargs['version']
    else:
      vermatch = VER_X_REGEX.match(self.ptr.version)
      if vermatch:
        # for interop with 3rd party repofiles that use $releasever
        self.version = vermatch.group(1)
      else:
        self.version = self.ptr.version

  def save_release(self):
    if self.autofile.exists():
      root = rxml.tree.read(self.autofile).get('/distribution')
    else:
      root = rxml.tree.Element('distribution')

    rpms     = rxml.tree.uElement('rpms', parent=root)
    parent   = rxml.tree.uElement(self.ptr.id, parent=rpms)
    release  = rxml.tree.uElement('release', parent=parent, text=self.release)

    root.write(self.autofile)

    if self.ptr._config.file.exists():
      # set the mode and ownership of .dat file to match definition file.
      st = self.ptr._config.file.stat()
      self.autofile.chown(st.st_uid, st.st_gid)
      self.autofile.chmod(st.st_mode)

  def check_release(self):
    if ( self.release == '0' or
         not self.autofile.exists() or
         not self.ptr.mdfile.exists() or
         self.ptr.diff.input.difference() or
         self.ptr.diff.variables.difference() or
         self.ptr.diff.config.difference() ):
      self.release = str(int(self.release)+1)

  def write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'

    spec = ConfigParser()

    # metadata section
    M = 'metadata'
    spec.add_section(M)

    spec.set(M, 'name',             self.name)
    spec.set(M, 'long_description', self.desc)
    spec.set(M, 'description',      self.summary)
    spec.set(M, 'author',           self.author)
    spec.set(M, 'version',          self.version)

    if self.license: spec.set(M, 'license', self.license)

    # bdist_rpm section
    B = 'bdist_rpm'
    spec.add_section(B)

    spec.set(B, 'force_arch',        self.arch)
    spec.set(B, 'distribution_name', self.fullname)
    spec.set(B, 'release',           self.release)

    if self.provides:  spec.set(B, 'provides',  ' '.join(self.provides))
    if self.requires:  spec.set(B, 'requires',  ' '.join(self.requires))
    if self.obsoletes: spec.set(B, 'obsoletes', ' '.join(self.obsoletes))

    # get the various script types
    build   = self.ptr.get_build()
    clean   = self.ptr.get_clean()
    install = self.ptr.get_install()
    post    = self.ptr.get_post()
    postun  = self.ptr.get_postun()
    pre     = self.ptr.get_pre()
    prep    = self.ptr.get_prep()
    preun   = self.ptr.get_preun()
    verify  = self.ptr.get_verifyscript()

    triggers = self.ptr.get_triggers()

    ghost = self.ptr.get_ghost_files()

    # add to bdist_rpm
    if build:   spec.set(B, 'build_script',   build)
    if clean:   spec.set(B, 'clean_script',   clean)
    if install: spec.set(B, 'install_script', install)
    if post:    spec.set(B, 'post_install',   post)
    if postun:  spec.set(B, 'post_uninstall', postun)
    if pre:     spec.set(B, 'pre_install',    pre)
    if prep:    spec.set(B, 'prep_script',    prep)
    if preun:   spec.set(B, 'pre_uninstall',  preun)
    if verify:  spec.set(B, 'verify_script',  verify)

    if triggers:
      trigcfg = self.build_folder / 'triggers.cfg'
      triggers.write_config(trigcfg)
      spec.set(B, 'trigger_configs', trigcfg)

    if ghost: spec.set(B, 'ghost_files', '\n\t'.join(ghost))

    # distribution related data
    D = 'distribution'
    spec.add_section(D)

    self.add_data_files(spec, D)
    self.add_config_files(spec, B)
    self.add_doc_files(spec, B)

    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def write_manifest(self):
    manifest = ['setup.py', 'setup.cfg']
    manifest.extend( [ x.relpathfrom(self.build_folder) for x in
                       self.source_folder.findpaths(
                         type=pps.constants.TYPE_NOT_DIR) ])
    (self.build_folder/'MANIFEST').write_lines(manifest)

  def add_data_files(self, spec, section):
    data = []
    for dir, files in self.data_files.items():
      data.append('\t%s : %s' % (dir, ', '.join(files)))
    if data: spec.set(section, 'data_files', '\n'.join(data))

  def add_config_files(self, spec, section):
    cfg = []
    for dir,files in self.data_files.items():
      if dir.startswith('/etc'): # config files
        cfg.extend([ dir/x.basename for x in files ])
    if cfg: spec.set(section, 'config_files', '\n\t'.join(cfg))

  def add_doc_files(self, spec, section):
    doc = []
    if (self.source_folder / 'COPYING').exists():
      doc.append('COPYING')
    for dir,files in self.data_files.items():
      if dir.startswith('/usr/share/doc'):
        doc.extend([ dir/x.basename for x in files ])
    if doc: spec.set(section, 'doc_files', '\n\t'.join(doc))

  def sign(self):
    pubkey = self.ptr.mddir/GPGKEY_NAME
    seckey = self.ptr.mddir/GPGKEY_NAME+'-private'

    pubkey.write_text(PUBKEY)
    seckey.write_text(SECKEY)

    mkrpm.signRpms([self.rpm_path], public=pubkey, secret=seckey, 
                   passphrase='', working_dir=self.ptr.TEMP_DIR)


class TriggerContainer(list):
  def __init__(self, iterable=None):
    iterable = iterable or []
    self.check(iterable)
    list.__init__(self, iterable)

  def write_config(self, file):
    lines = []
    for trigger in self:
      lines.append(str(trigger))
      lines.append('')
    file.write_lines(lines)

  def extend(self, item):
    self.check(item)
    list.extend(self, item)

  def append(self, item):
    self.check(item)
    list.append(self, item)

  def insert(self, index, item):
    self.check(item)
    list.insert(self, index, item)

  def check(self, item):
    if not hasattr(item, '__iter__'):
      item = [item]
    if isinstance(item, Trigger):
      return
    for x in item:
      if not isinstance(x, Trigger):
        raise TypeError("Trying to add non-Trigger object '%s' to TriggerContainer" % x)


class Trigger(dict):
  def __init__(self, id, **kwargs):
    self.id = id
    dict.__init__(self, **kwargs)

  def __str__(self):
    lines = ['[%s]' % self.id]
    if 'triggerid' not in self:
      lines.append('triggerid = %s' % self.id)
    for key, value in self.iteritems():
      if hasattr(value, '__iter__'):
        val = '\n\t'.join(value)
        lines.append('%s = %s' % (key, val.strip('\n')))
      else:
        lines.append('%s = %s' % (key, value))
    return '\n'.join(lines)


class RpmBuildFailedException(SystemStudioError):
  message = "RPM build failed.  See build output below for details:\n%(message)s"

PUBKEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

mQGiBE1/0xURBACQJRY9A78vnkweEeUgRcqP32R81E4H3VdV1O5oa3qfw7niUrDV
bN2kwG+TvbJ9HvqcbutosO98zd32zAkK9+U8caO558ezimb+AdV4+j5Bwb3BT+RQ
ijMUb/V1kz7SuSmvIGiWGsAK3vl6oqdWaIxX1676tlKWpEoqZ7Xoa1ksMwCg8VTY
rHFG/DaqHoGWXGMvvhxwRWMEAIbN8pbAL219Ag4CzRH6mwq7BUhp8ZsCzb8HXguw
4IZJIiYONWOKaXgswMqw8MIkSsytP1Mnll6pnWytWhkPeV0gpZXB/AXt7spnf9oO
Kqj61GtvNxhSWyVfNu8oERq3+r8O65RE1b54cDcR0ruBJ+NXzpVlEb66ktEG9LDG
5iZcA/4hNVf1H3xoXj2Edb+vXQnAcYg5PaF/VX0kUj51wsswuwEWw80+fN/BjQ8F
83qQc0wbwHKXuHXti36H7kp6A9CqXcpVZxteVkF5qD5bBD3Mwe1OJ39PnpScNPz7
x+9WDg7BPTL+uV8pxzh84+ZY+7J5pVJZO7kfhyB1/b+NN2u+GLQ2U3lzdGVtU3R1
ZGlvIChkZWZhdWx0KSA8Y29udGFjdEByZW5kaXRpb25zb2Z0d2FyZS5jb20+iGAE
ExECACAFAk1/0xUCGwMGCwkIBwMCBBUCCAMEFgIDAQIeAQIXgAAKCRBJPcZmw2tS
vfPRAKCbcDmNPL3bIQSfJol+ba+yY649pQCgsjWeVeIKv1HpzcgS+8NH+3L9lqS5
Ag0ETX/THRAIALFSgBTWPi2vIjCwraod81rUBI3eZfvdwiur9XNXWceDTBBcQDJA
65mz7DhDthCuYclmRwW16jisU++Sox8lu2p/EF6qkxoCdP51wMIKWEgVdT34fvDL
2adkPsylURdE0lddYTWr0uV+zchJE6iOPveaMgaSga1vJgEH1kZqKl6GUE0tvaj+
YBBfn7YL1AiL9fIOqW/Fe7sTQE9uJfgtF/qlsQWjk95PzlWZ3zxEjER3dJ39n7l2
z7wV8D7uKMziLg3T1K/dhXAu3j5GKoIJTg6tDByAvTnvZrH9fanZ0BII7PAhcd3X
8N1/vXQJFU7afIrkLRBLpsOt9W4m87/ruesAAwYH/3Mz2a9CY/DMaMe41jQUVN2z
9ImaipTIvxAzfKnfoQprw6eX/y0PY+widMZAhfNT+hCVgQy+4hQ3GnHXSwxSwGyp
dRIVRUI/yHWSde9yuEeW4BJaRCTtl5tCBMlckzSYUYFonBFILb5DSeCyX9dzIDSA
kJZ32Gs/nkg8vlHNOc+sxfHtreoZ3dt3guzUTp2pH+Lq/ugxXotmt88HASRZdZjM
71DlerOAicXjS3oXIuTMyse0z74E9jQRI1/5cl5J6RDYYpC0pVLwvWWLjSBqK7+7
z+RUEusrZkFmbHJzZ+5OSREozZFKFUEfo+xJEdjqXfK+r57ZX9S0Xui4HC+4U02I
SQQYEQIACQUCTX/THQIbDAAKCRBJPcZmw2tSvZBHAJ4k/u19038qysemGjjd+bck
KZusQgCgwE/h4YciTPrUdpXk/Ike9CdKSCc=
=yAM/
-----END PGP PUBLIC KEY BLOCK-----"""

SECKEY="""-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

lQG7BE1/0xURBACQJRY9A78vnkweEeUgRcqP32R81E4H3VdV1O5oa3qfw7niUrDV
bN2kwG+TvbJ9HvqcbutosO98zd32zAkK9+U8caO558ezimb+AdV4+j5Bwb3BT+RQ
ijMUb/V1kz7SuSmvIGiWGsAK3vl6oqdWaIxX1676tlKWpEoqZ7Xoa1ksMwCg8VTY
rHFG/DaqHoGWXGMvvhxwRWMEAIbN8pbAL219Ag4CzRH6mwq7BUhp8ZsCzb8HXguw
4IZJIiYONWOKaXgswMqw8MIkSsytP1Mnll6pnWytWhkPeV0gpZXB/AXt7spnf9oO
Kqj61GtvNxhSWyVfNu8oERq3+r8O65RE1b54cDcR0ruBJ+NXzpVlEb66ktEG9LDG
5iZcA/4hNVf1H3xoXj2Edb+vXQnAcYg5PaF/VX0kUj51wsswuwEWw80+fN/BjQ8F
83qQc0wbwHKXuHXti36H7kp6A9CqXcpVZxteVkF5qD5bBD3Mwe1OJ39PnpScNPz7
x+9WDg7BPTL+uV8pxzh84+ZY+7J5pVJZO7kfhyB1/b+NN2u+GAAAoKauMH2lDwCB
qk1F5jFVjTCVZ6LaCbO0NlN5c3RlbVN0dWRpbyAoZGVmYXVsdCkgPGNvbnRhY3RA
cmVuZGl0aW9uc29mdHdhcmUuY29tPohgBBMRAgAgBQJNf9MVAhsDBgsJCAcDAgQV
AggDBBYCAwECHgECF4AACgkQST3GZsNrUr3z0QCgm3A5jTy92yEEnyaJfm2vsmOu
PaUAoLI1nlXiCr9R6c3IEvvDR/ty/ZaknQI9BE1/0x0QCACxUoAU1j4tryIwsK2q
HfNa1ASN3mX73cIrq/VzV1nHg0wQXEAyQOuZs+w4Q7YQrmHJZkcFteo4rFPvkqMf
JbtqfxBeqpMaAnT+dcDCClhIFXU9+H7wy9mnZD7MpVEXRNJXXWE1q9Llfs3ISROo
jj73mjIGkoGtbyYBB9ZGaipehlBNLb2o/mAQX5+2C9QIi/XyDqlvxXu7E0BPbiX4
LRf6pbEFo5PeT85Vmd88RIxEd3Sd/Z+5ds+8FfA+7ijM4i4N09Sv3YVwLt4+RiqC
CU4OrQwcgL0572ax/X2p2dASCOzwIXHd1/Ddf710CRVO2nyK5C0QS6bDrfVuJvO/
67nrAAMGB/9zM9mvQmPwzGjHuNY0FFTds/SJmoqUyL8QM3yp36EKa8Onl/8tD2Ps
InTGQIXzU/oQlYEMvuIUNxpx10sMUsBsqXUSFUVCP8h1knXvcrhHluASWkQk7Zeb
QgTJXJM0mFGBaJwRSC2+Q0ngsl/XcyA0gJCWd9hrP55IPL5RzTnPrMXx7a3qGd3b
d4Ls1E6dqR/i6v7oMV6LZrfPBwEkWXWYzO9Q5XqzgInF40t6FyLkzMrHtM++BPY0
ESNf+XJeSekQ2GKQtKVS8L1li40gaiu/u8/kVBLrK2ZBZmxyc2fuTkkRKM2RShVB
H6PsSRHY6l3yvq+e2V/UtF7ouBwvuFNNAAFUDNI0RaMS9q+00BSIvnZhOFlVC/A4
1h/mNQ0bt5njCbAK3qRXa8QcNah1UxPLiEkEGBECAAkFAk1/0x0CGwwACgkQST3G
ZsNrUr2QRwCdHUhS1k6WvjMkaoJ90E/KFiPdKRgAoKFOArbX2eNsTFADcS3wCJX+
mIJX
=q1x+
-----END PGP PRIVATE KEY BLOCK-----"""

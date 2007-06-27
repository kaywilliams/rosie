from os.path import join

import re

from dims.osutils import find

import dims.filereader as filereader
import dims.xmltree as xmltree

from dimsbuild.event import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib import RpmsHandler, RpmsInterface

EVENTS = [
  {
    'id': 'default-theme-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'RPMS',
    'provides': 'default-theme-info',
  },
]

HOOK_MAPPING = {
  'DefaultThemeHook': 'default-theme-rpm',
  'PkglistHook'     : 'pkglist',
  'ValidateHook'    : 'validate',
}

RPM_PNVR_REGEX = re.compile('([.*]?.+-.+-.+)\..+\.[Rr][Pp][Mm]')

API_VERSION = 4.0

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'default_theme.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('//default-theme-rpm', schemafile='default-theme-rpm.rng')

class PkglistHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'default_theme.pkglist'
    self.interface = interface
    self.productid = self.interface.config.get('//main/product/text()')

  def post(self):
    for pkg in self.interface.cvars.get('pkglist', []):
      if pkg.startswith('gdm'):
        default_theme_info = self.interface.cvars.get('default-theme-info', None)
        if default_theme_info is not None:
          rpmname, nvr, type, requires = default_theme_info # for convenience
          
          attrs = {'type': type or 'mandatory'}
          if requires is not None:
            attrs['requires'] = requires

          if nvr not in self.interface.cvars['pkglist']:
            # add the rpm to the pkglist
            self.interface.cvars['pkglist'].append(nvr)
            self.interface.cvars['pkglist'].sort()            
            filereader.write(self.interface.cvars['pkglist'], self.interface.cvars['pkglist-file'])

          # add the rpm information to the comps.xml
          if rpmname not in self.interface.cvars['required-packages']:
            self.interface.cvars['required-packages'].append(rpmname)
          
          compstree = xmltree.read(self.interface.cvars['comps-file'])
          group = compstree.get('//group[id/text() = "%s"]' %self.productid)
          packagelist = group.get('packagelist', None)
          if packagelist is None:
            packagelist = xmltree.Element('packagelist', parent=group)
          if packagelist.get('packagereq[text() = "%s"]' %rpmname, None) is None:
            packagereq = xmltree.Element('packagereq', parent=packagelist, text=rpmname, attrs=attrs)
            compstree.write(self.interface.cvars['comps-file'])
        break    
    
class DefaultThemeHook(RpmsHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'default_theme.default-theme-rpm'
    
    data = {
      'config': [
        '//rpms/default-theme-rpm',
      ],
      'output': [
        join(interface.METADATA_DIR, 'default-theme-rpm/'),
      ],
    }

    self.themename = interface.config.get('//rpms/default-theme-rpm/theme/text()', interface.product)

    RpmsHandler.__init__(self, interface, data, 'default-theme-rpm',
                         '%s-default-theme' %(interface.product,),
                         description='Script to set default gdm graphical theme',
                         long_description='The %s-default-theme package requires the gdm package. '
                         ' Its sole function is to modify the value of the GraphicalTheme attribute in'
                         ' /usr/share/gdm/defaults.conf to the %s theme' %(interface.product,
                                                                           self.themename,))

  def apply(self): pass  

  def post(self):
    try:      
      rpm = find(join(self.interface.METADATA_DIR, 'localrepo', 'RPMS'),
                 name='%s*.[Rr][Pp][Mm]' %(self.rpmname,), prefix=False)[0]
      self.interface.cvars['default-theme-info'] = (self.rpmname,
                                                    RPM_PNVR_REGEX.match(rpm).groups()[0],
                                                    'conditional', 'gdm')
    except IndexError:
      if self.test_build_rpm() and not self.interface.isSkipped(self.id):
        raise RuntimeError("missing rpm: '%s'" %(self.rpmname,))
      else:
        self.interface.cvars['default-theme-info'] = None

  def _get_requires(self):
    return 'gdm'
  
  def _get_post_install(self):
    f = open(join(self.output_location, 'postinstall.sh'), 'w')
    f.write(SCRIPT %(self.themename,))
    f.close()
    return 'postinstall.sh'

    
SCRIPT = """
chmod +w /usr/share/gdm/defaults.conf
sed -i 's/^GraphicalTheme=[a-zA-Z]*$/GraphicalTheme=%s/g' /usr/share/gdm/defaults.conf
chmod -w /usr/share/gdm/defaults.conf
"""
    

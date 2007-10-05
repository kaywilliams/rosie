from dims import pps

from dimsbuild.event import Event

from dimsbuild.modules.shared.rpms import InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

class ConfigRpmEvent(Event, RpmBuildMixin, InputFilesMixin):
  def __init__(self):
    Event.__init__(self, id='config-rpm',
                   provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info'])
    RpmBuildMixin.__init__(self,
                           '%s-config' % self.product,
                           'The %s-config provides scripts and supporting '\
                           'files for configuring the %s '\
                           'distribution.' %(self.product, self.fullname),
                           '%s configuration script and supporting files' % self.fullname)
    InputFilesMixin.__init__(self)
    
    self.installinfo = {
      'config' : ('config/script', '/usr/lib/%s' % self.product),
      'support': ('config/supporting-files', '/usr/lib/%s' % self.product)
    }
    
    self.DATA = {
      'variables': ['product', 'fullname', 'pva'],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }
  
  def setup(self):
    self._setup_build()
    self._setup_download()
  
  def run(self):
    self.io.clean_eventcache(all=True)
    if self._test_build('True'):
      self._build_rpm()
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    if not self._test_build('True'):
      return
    self._check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []
    self.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))
  
  def _generate(self):
    self.io.sync_input()
  
  def _get_files(self):
    sources = {}
    sources.update(RpmBuildMixin._get_files(self))
    sources.update(InputFilesMixin._get_files(self))
    return sources
  
  def _test_build(self, default):
    if RpmBuildMixin._test_build(self, default):
      if self.config.get('requires', None) or \
         self.config.get('obsoletes', None) or \
         self.config.get('config/script/path/text()', None) or \
         self.config.get('config/supporting-files/path/text()', None) or \
         self.cvars['%s-content' % self.id]:
        return True
    return False
  
  def _getpscript(self):
    post_install_scripts = self.io.list_output(what=self.installinfo['config'])
    try:
      return post_install_scripts[0]
    except IndexError:
      return None

EVENTS = {'rpms': [ConfigRpmEvent]}

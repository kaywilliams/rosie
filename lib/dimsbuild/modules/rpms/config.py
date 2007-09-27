from dims import pps

from dimsbuild.modules.rpms.lib import FileDownloadMixin, RpmBuildEvent

P = pps.Path

API_VERSION = 5.0

class ConfigRpmEvent(RpmBuildEvent, FileDownloadMixin):
  def __init__(self):
    self.installinfo = {
      'config' : ('/distro/rpms/config-rpm/config/script/path',
                  '/usr/lib/%s' % self.product),
      'support': ('/distro/rpms/config-rpm/config/supporting-files/path',
                  '/usr/lib/%s' % self.product),
    }
    
    self.DATA = {
      'variables': ['product', 'fullname'],
      'config': [
        '/distro/rpms/config-rpm',
      ],
      'input':  [],
      'output': [],
    }
    
    RpmBuildEvent.__init__(self,
                           '%s-config' % self.product,
                           'The %s-config provides scripts and supporting '\
                           'files for configuring the %s '\
                           'distribution.' %(self.product, self.fullname),
                           '%s configuration script and supporting files' % self.fullname,
                           id='config-rpm')
    FileDownloadMixin.__init__(self)
        
  def validate(self):
    self.validator.validate('/distro/rpms/config-rpm', 'config-rpm.rng')

  def setup(self):
    RpmBuildEvent.setup(self)
    FileDownloadMixin.setup(self)
    
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

  def _get_files(self):
    sources = {}
    sources.update(RpmBuildEvent._get_files(self))
    sources.update(FileDownloadMixin._get_files(self))
    return sources
  
  def _test_build(self, default):
    if RpmBuildEvent._test_build(self, default):
      if self.config.get('//config-rpm/requires', None) or \
         self.config.get('//config-rpm/obsoletes', None) or \
         self.config.get('//config-rpm/config/script/path/text()', None) or \
         self.config.get('//config-rpm/config/supporting-files/path/text()', None) or \
         self.srcdir.findpaths():
        return True
    return False
  
  def _getpscript(self):
    script = self.config.get(self.installinfo['config'][0], None)
    if script:
      post_install_scripts = self.output_location.findpaths(glob=P(script).basename)
      assert len(post_install_scripts) == 1
      return post_install_scripts[0]
    return None

EVENTS = {'RPMS': [ConfigRpmEvent]}

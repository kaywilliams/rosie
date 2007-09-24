import os

from dims import shlib

from dimsbuild.event   import Event
from dimsbuild.logging import L0, L1

API_VERSION = 5.0

class CreaterepoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'createrepo',
      provides = ['rpms', 'rpms-directory', 'repodata-directory'],
      requires = ['cached-rpms'],
      conditionally_requires = ['comps-file', 'gpgsign-enabled', 'signed-rpms'],
    )
    
    self.cvars['repodata-directory'] = self.SOFTWARE_STORE/'repodata'

    self.DATA = {
      'variables': ['product'],
      'input':     [],
      'output':    [self.cvars['repodata-directory']]
    }
    
  def setup(self):
    self.diff.setup(self.DATA)

    self.cvars['rpms-directory'] = self.SOFTWARE_STORE/self.product

    if self.cvars['comps-file']:
      self.DATA['input'].append(self.cvars['comps-file'])
    
    if self.cvars['gpgsign-enabled']:
      self.io.setup_sync(self.cvars['rpms-directory'], 
                      paths=self.cvars['signed-rpms'], id='rpms')
    else:
      self.io.setup_sync(self.cvars['rpms-directory'], 
                      paths=self.cvars['cached-rpms'], id='rpms')
  
  def run(self):
    self.log(0, L0("creating repository metadata"))
    
    self.io.remove_output()
    self.io.sync_input(copy=True, link=True)

    # run createrepo
    self.log(1, L1("running createrepo"))
    pwd = os.getcwd()
    os.chdir(self.SOFTWARE_STORE)
    shlib.execute('/usr/bin/createrepo -q -g %s .' % self.cvars['comps-file'])
    os.chdir(pwd)
    
    self.diff.write_metadata()
  
  def apply(self):
    self.cvars['rpms'] = self.io.list_output(what='rpms')


EVENTS = {'SOFTWARE': [CreaterepoEvent]}

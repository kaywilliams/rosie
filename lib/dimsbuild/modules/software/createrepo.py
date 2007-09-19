import os

from dims import shlib

from dimsbuild.event     import Event

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
      'input':   [],
      'output':  [self.cvars['repodata-directory']]
    }
    
  def setup(self):
    self.setup_diff(self.DATA)

    self.cvars['rpms-directory'] = self.SOFTWARE_STORE/self.cvars['base-vars']['product']

    if self.cvars['gpgsign-enabled']:
      self.setup_sync(self.cvars['rpms-directory'], 
                      paths=self.cvars['signed-rpms'], id='rpms')
    else:
      self.setup_sync(self.cvars['rpms-directory'], 
                      paths=self.cvars['cached-rpms'], id='rpms')
  
  def run(self):
    self.log(0, "running createrepo")
    
    self.remove_output()
    self.sync_input(copy=True, link=True)

    # run createrepo
    self.log(1, "running createrepo")
    pwd = os.getcwd()
    os.chdir(self.SOFTWARE_STORE)
    shlib.execute('/usr/bin/createrepo -q -g %s .' % self.cvars['comps-file'])
    os.chdir(pwd)
    
    self.write_metadata()
  
  def apply(self):
    self.cvars['rpms'] = self.list_output(what='rpms')


EVENTS = {'SOFTWARE': [CreaterepoEvent]}

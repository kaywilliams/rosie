"""
base-info.py

provides information about the base distribution
"""
from rendition import FormattedFile as ffile
from rendition import img

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event
from spin.logging   import L1

API_VERSION = 5.0
EVENTS = {'setup': ['BaseInfoEvent']}

class BaseInfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'base-info',
      provides = ['base-info'],
      requires = ['anaconda-version', 'base-repoid'],
    )

    self.DATA =  {
      'input':     [],
      'output':    [],
    }

  def error(self, e):
    Event.error(self, e)
    try:
      self.image.close()
    except:
      pass

  def setup(self):
    self.diff.setup(self.DATA)

    initrd_in=self.cvars['repos'][self.cvars['base-repoid']].osdir/\
              self.locals.files['isolinux']['initrd.img']['path']

    self.io.add_fpath(initrd_in, self.mddir, id='initrd.img')
    self.initrd_out = self.io.list_output(what='initrd.img')[0]
    self.buildstamp_out = self.mddir/'.buildstamp'
    self.DATA['output'].append(self.buildstamp_out)

  def run(self):
    self.log(2, L1("reading buildstamp file from base repository"))

    # download initrd.img
    self.io.sync_input(cache=True, callback=Event.link_callback, text=None)

    # extract buildstamp
    image = self.locals.files['isolinux']['initrd.img']
    self.image = img.MakeImage(self.initrd_out, image['format'], image.get('zipped', False))
    self.image.open('r')
    self.image.read('.buildstamp', self.mddir)
    self.image.close()
    img.cleanup()

    # update metadata
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    # parse buildstamp
    buildstamp = ffile.DictToFormattedFile(self.locals.buildstamp_fmt)
    # update base vars
    try:
      self.cvars['base-info'] = buildstamp.read(self.buildstamp_out)
    except:
      pass # caught by verification

  def verify_buildstamp_file(self):
    "verify buildstamp file exists"
    self.verifier.failUnlessExists(self.buildstamp_out)
  def verify_base_vars(self):
    "verify base-info cvar"
    self.verifier.failUnless(self.cvars['base-info'])

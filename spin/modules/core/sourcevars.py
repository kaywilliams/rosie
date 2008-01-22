"""
sourcevars.py

provides information about the source distribution
"""
from rendition import FormattedFile as ffile
from rendition import img

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event

API_VERSION = 5.0
EVENTS = {'setup': ['SourceVarsEvent']}

class SourceVarsEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'source-vars',
      provides = ['source-vars'],
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
    # download input files
    self.io.sync_input(cache=True)

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
    # update source vars
    try:
      self.cvars['source-vars'] = buildstamp.read(self.buildstamp_out)
    except:
      pass # caught by verification

  def verify_buildstamp_file(self):
    "verify buildstamp file exists"
    self.verifier.failUnlessExists(self.buildstamp_out)
  def verify_source_vars(self):
    "verify source-vars cvar"
    self.verifier.failUnless(self.cvars['source-vars'])

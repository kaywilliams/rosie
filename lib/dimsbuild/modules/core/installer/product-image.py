from dims import filereader
from dims import pps
from dims import sortlib
from dims import xmllib

from dimsbuild.event   import Event
from dimsbuild.logging import L0

from dimsbuild.modules.shared.installer import ImageModifyMixin

P = pps.Path


API_VERSION = 5.0


class ProductImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'product-image',
      provides = ['product.img'],
      requires = ['anaconda-version', 'buildstamp-file',
                  'comps-file', 'base-repoid'],
      conditionally_requires = ['product-image-content'],
    )
    
    self.DATA = {
      'config':    ['/distro/product-image/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'product.img')
  
  def validate(self):
    self.validator.validate('/distro/product-image', 'product.rng')
    
  def error(self, e):
    Event.error(e)
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    self.DATA['input'].append(self.cvars['buildstamp-file'])
    self.image_locals = self.locals.files['installer']['product.img']
    ImageModifyMixin.setup(self)
  
  def run(self):
    self.log(0, L0("generating product.img"))
    self._modify()
  
  def apply(self):
    self.io.clean_eventcache()
    for file in self.io.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    
    # generate installclasses if none exist
    if len((P(self.image.handler._mount)/'installclasses').findpaths(glob='*.py')) == 0:
      self._generate_installclass()
    
    # write the buildstamp file to the image
    self._write_buildstamp()
  
  def _generate_installclass(self):
    comps = xmllib.tree.read(self.cvars['comps-file'])
    groups = comps.xpath('//group/id/text()')
    defgroups = comps.xpath('//group[default/text() = "true"]/id/text()')
    
    # try to perform the replacement; skip if it doesn't work
    try:
      installclass = self.locals.installclass % (defgroups, groups)
    except TypeError:
      installclass = self.locals.installclass
    
    self.image.writeflo(filereader.writeFLO(installclass),
                        filename='custom.py', dest='installclasses')


EVENTS = {'INSTALLER': [ProductImageEvent]}

import copy

import os

from os.path import join, isfile, exists

import dims.osutils as osutils
import dims.xmltree as xmltree
import dims.listcompare as listcompare
import dims.sortlib as sortlib

from dims.ConfigLib import ConfigError
from dims.CacheManager import CacheManagerError

from interface import EventInterface, VersionMixin, FlowControlROMixin
from event import EVENT_TYPE_PROC, EVENT_TYPE_MARK, EVENT_TYPE_MDLR

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'comps',
    'interface': 'CompsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['comps.xml'],
    'requires': ['.discinfo', 'stores'],
  },
]

HEADER_FORMAT = "<?xml version='%s' encoding='%s'?>"

TYPES = ['mandatory', 'optional', 'required', 'default']
KERNELS = ['kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
           'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
           'kernel-BOOT']


class CompsInterface(EventInterface, VersionMixin, FlowControlROMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    VersionMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()))
    FlowControlROMixin.__init__(self)
    self.mdgroupfile = join(self._base.METADATA, 'comps.xml')
    self.storegroupfileloc = join(self._base.SOFTWARE_STORE,
                                  self._base.base_vars['product'],
                                  'base')
  
  def getCompsFile(self):
    return self._base.COMPS_FILE
  def setCompsFile(self, file):
    self._base.COMPS_FILE = file
  
  def getRequiredPackages(self):
    try:
      return self._base.reqpkgs
    except AttributeError:
      return None
  def setRequiredPackages(self, reqpkgs):
    self._base.reqpkgs = reqpkgs
  

#---------- HOOK FUNCTIONS ----------#
def init_hook(interface):
  parser = interface.getOptParser('build')
  
  # the following option doesn't work yet
  parser.add_option('--with-comps',
                    default=None,
                    dest='with_comps',
                    metavar='COMPSFILE',
                    help='use COMPSFILE for the comps.xml instead of generating one')

#def applyopt_hook(interface):
#  interface.setEventControlOption('comps', interface.options.do_comps)

def precomps_hook(interface):
  interface.disableEvent('comps')
  # if the input stores changes, we need to run
  # if there is no comps file in the ouput directory, and one isn't otherwise
  # specified, we do need to run
  if interface.getFlag('inputstore-changed'):
    interface.enableEvent('comps')
  elif not exists(join(interface.getMetadata(), 'comps.xml')) and \
     interface.getCompsFile() is None:
    interface.enableEvent('comps')
  interface.setFlag('comps-changed', False)

def comps_hook(interface):
  interface.log(0, "computing required packages")
  compshandler = CompsHandler(interface)

  groupfile = interface.config.get('//main/groupfile/text()', None)
  if groupfile is not None:
    interface.log(1, "reading supplied comps file")
    reqpkgs = xmltree.read(groupfile).get('//packagereq/text()')
  else:
    interface.log(1, "resolving required groups and packages")
    compshandler.generateComps()
    reqpkgs = compshandler.comps.get('//packagereq/text()')
  
  if isfile(interface.mdgroupfile):
    oldreqpkgs = xmltree.read(interface.mdgroupfile).get('//packagereq/text()')
  else:
    oldreqpkgs = []
  
  reqpkgs.sort()
  oldreqpkgs.sort()
  
  # test if required packages have changed
  old, new, _ = listcompare.compare(oldreqpkgs, reqpkgs)
  # if they have, write out new required packages and notify that pkglist needs to be regenerated
  if len(old) > 0 or len(new) > 0:
    interface.log(1, "required packages have changed")
    if groupfile is not None:
      osutils.cp(groupfile, interface.mdgroupfile)
    else:
      interface.log(1, "writing comps.xml")
      compshandler.comps.write(interface.mdgroupfile)
      os.chmod(interface.mdgroupfile, 0644)
    interface.setFlag('comps-changed', True)
  else:
    interface.log(1, "required packages unchanged")

def postcomps_hook(interface):  
  # copy groupfile
  if interface.getCompsFile() is None:
    interface.setCompsFile(interface.mdgroupfile)
  osutils.mkdir(interface.storegroupfileloc, parent=True)
  osutils.cp(interface.getCompsFile(), interface.storegroupfileloc)
  
  # set required packages
  reqpkgs = xmltree.read(interface.getCompsFile()).get('//packagereq/text()')
  interface.setRequiredPackages(reqpkgs)
  

class CompsHandler:
  def __init__(self, interface, xmlversion='1.0', xmlencoding='UTF-8'):
    self.interface = interface
    self.comps = xmltree.Tree('comps')
    self.comps.setheader(HEADER_FORMAT % (xmlversion, xmlencoding))
    self.config = self.interface.config
  
  def generateComps(self):
    product  = self.config.get('//main/product/text()')
    fullname = self.config.get(['//main/fullname/text()', '//main/product/text()'])
    base_store = self.interface.getBaseStore()
    
    mapped, unmapped = self.__map_groups()
    groupfiles = self.__get_groupfiles()
    
    # create base distro group
    base = None
    packages = self.config.mget('//main/packages/package/text()')
    base = Group(product, fullname, 'This group includes packages specific to %s' % fullname)
    if len(packages) > 0:
      self.comps.getroot().append(base)
      for package in packages:
        self.add_group_package(package, base, type='mandatory')
    
    processed = [] # processed groups
    
    # process groups
    for groupfileid, path, in groupfiles:
        # read groupfile
        try:
          tree = xmltree.read(path)
        except ValueError, e:
          print e
          raise CompsError, "the file '%s' does not exist" % file
      
        # add the 'core' group of the base store
        if groupfileid == base_store:
          try:
            self.add_group_by_id('core', tree, mapped[groupfileid])
            processed.append('core')
          except IndexError:
            pass
      
        # process mapped groups - each MUST be processed or we raise an exception
        while len(mapped[groupfileid]) > 0:
          groupid = mapped[groupfileid].pop(0)
          if groupid in processed: continue # skip those we already processed
          self.add_group_by_id(groupid, tree, mapped[groupfileid])
          processed.append(groupid)
      
        # process unmapped groups - these do not need to be processed at each step
        i = 0; j = len(unmapped['unmapped'])
        while i < j:
          groupid = unmapped['unmapped'][i]
          if groupid in processed:
            i += 1; continue
          try:
            group = tree.get('//group[id/text()="%s"]' % groupid)[0]
            self.add_group_by_id(groupid, tree, unmapped['unmapped'], processed)
            processed.append(unmapped['unmapped'].pop(i))
            j = len(unmapped['unmapped'])
          except IndexError:
            i += 1
    
    if 'core' not in processed:
      raise CompsError, "The base store '%s' does not appear to define a 'core' group in any of its comps.xml files" % base_store
    
    # if any unmapped group wasn't processed, raise an exception
    if len(unmapped['unmapped']) > 0:
      raise ConfigError, "Unable to resolve all groups in available stores: missing %s" % unmapped['unmapped']
    
    # check to make sure a 'kernel' pacakge or equivalent exists - kinda icky
    allpkgs = self.comps.get('//packagereq/text()')
    found = False
    for kernel in KERNELS:
      if kernel in allpkgs:
        found = True; break
    
    if not found:
      # base is defined above, it is the base group for the repository
      if len(packages) == 0: self.comps.getroot().insert(0, base) # HAK HAK HAK
      self.add_group_package('kernel', base, type='mandatory')
    
    # add category
    ver = self.interface.anaconda_version
    cat = Category('Groups', fullname=fullname, version=ver)
    self.comps.getroot().append(cat)
    for group in self.comps.getroot().get('//group/id/text()'):
      self.add_category_group(group, cat, ver)
  
  def __map_groups(self):
    groups = self.config.mget('//main/groups/group')
    
    mapped = {}
    for store in self.config.mget('//stores/*/store/@id'):
      mapped[store] = []
    unmapped = {'unmapped': []} # done this way for consistency with mapped
    # an improvement might be to combine mapped and unmapped, reserving the keyword 'unmapped'
    
    for group in groups:
      store = group.attrib.get('store', None)
      if store is not None:
        try:
          mapped[store].append(group.text)
        except KeyError:
          raise ConfigError, "Invalid store '%s' specified in group %s" % (store, group)
      else:
        unmapped['unmapped'].append(group.text)
    
    return mapped, unmapped
  
  def __get_groupfiles(self):
    "Get a list of all groupfiles in all repositories"
    #groupfiles = {}
    groupfiles = []
    
    for store in self.config.mget('//store/@id'):
      n,s,d,u,p = self.interface.getStoreInfo(store)
      
      repodatapath = self.config.get('//store[@id="%s"]/repodata-path/text()' % store, None)
      if repodatapath is not None:
        d = join(d, repodatapath) # TODO - this should accept absolute paths as well
      
      dest = join(self.interface.getInputStore(), n, d)
      osutils.mkdir('%s/repodata' % dest, parent=True) # TODO allow this to be config'd?
      
      try:
        groupfile = self.interface.cache(join(d, 'repodata/repomd.xml'), prefix=n, username=u, password=p)
      except CacheManagerError:
        raise ConfigError, "The '%s' store does not appear to be valid; unable to get groupfile from '%s'" % (store, join(d, 'repodata/repomd.xml'))
      
      try:
        groupfile = xmltree.read(join(dest, 'repodata/repomd.xml')).get('//data[@type="group"]/location/@href')
        if len(groupfile) > 0:
          self.interface.cache(join(d, groupfile[0]), prefix=n)
        groupfiles.append((store, join(self.interface.getInputStore(), n, d, groupfile[0])))
      except IndexError:
        pass # this is ok, not all repositories have groupfiles
      
    return groupfiles
  
  def add_group_package(self, package, group, requires=None, type='mandatory'):
    if type not in TYPES:
      raise ValueError, "Invalid type '%s', must be one of %s" % (type, TYPES)
    
    attrs = {}
    if requires is not None: attrs['requires'] = requires
    attrs['type'] = type
    
    packagelist = uElement('packagelist', parent = group)
    Element('packagereq', text=package, attrs=attrs, parent=packagelist)
  
  def add_group_by_id(self, groupid, tree, toprocess, processed=[]):
    group = tree.get('//group[id/text()="%s"]' % groupid)[0]
    
    # append is destructive, so copy() it
    self.comps.getroot().append(copy.deepcopy(group))
    
    # process any elements in the <grouplist> element
    groupreqs = tree.get('//group[id/text()="%s"]/grouplist/groupreq/text()' % groupid)
    for groupreq in groupreqs:
      if groupreq not in toprocess and groupreq not in processed:
        toprocess.append(groupreq)
  
  def add_category_group(self, group, category, version='0'):
    if sortlib.dcompare(self.interface.anaconda_version, '10.2.0.14-1') < 0:
      parent = category.iget('category/subcategories')
      Element('subcategory', parent=parent, text=group)
    else:
      parent = category.iget('grouplist')
      Element('groupid', parent=parent, text=group)

#------- FACTORY FUNCTIONS -------#
def Group(id, name, description='', default='true', uservisible='false', biarchonly='false'):
  group = Element('group')
  Element('id',          text=id,          parent=group)
  Element('name',        text=name,        parent=group)
  Element('description', text=description, parent=group)
  Element('default',     text=default,     parent=group)
  Element('uservisible', text=uservisible, parent=group)
  Element('biarchonly',  text=biarchonly,  parent=group)
  Element('packagelist', parent=group)
  return group

def Category(name, fullname='', version='0'):
  "Factory function for creating a category"
  if sortlib.dcompare(version, '10.2.0.14-1') < 0:
    top = Element('grouphierarchy')
    cat = Element('category', parent=top)
    uElement('name',          parent=cat, text='Groups')
    uElement('subcategories', parent=cat)
  else:
    top = Element('category')
    uElement('id',            parent=top, text=name)
    Element('name',           parent=top, text='Groups')
    Element('description',    parent=top, text='Groups in %s' % fullname)
    uElement('display_order', parent=top, text='99')
    list = uElement('grouplist', parent=top)
  return top

def uElement(name, parent, **kwargs):
  """Gets the child of the parent named name, or creates it if it doesn't exist.
  This is intended for use when an element tag is supposed to be unique to a
  parent - its behavior isn't very useful on nodes with multiple children having
  the same tag - it always returns the first child."""
  elem = parent.get(name, [])
  if len(elem) == 0:
    elem = xmltree.Element(name, parent=parent, **kwargs)
  else:
    elem = elem[0]
  return elem

def Element(name, parent=None, **kwargs):
  "Convenience function, merely calls the same factory function in xmltree"
  return xmltree.Element(name, parent=parent, **kwargs)

#--------- ERRORS ---------#
class CompsError(StandardError):
  "General comps error"

API_VERSION = 3.0

import Image
import ImageDraw
import ImageFilter
import ImageFont
import os
import dims.xmltree as xmltree

from dims.osutils import tree, basename, dirname, mkdir
from dims.sync import sync
from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface, LocalsMixin
from locals import L_LOGOS
from os.path import exists, join
from output import OutputEventMixin, OutputEventHandler

XmlPathError = xmltree.XmlPathError

EVENTS = [
  {
    'id': 'logos',
    'interface': 'LogosInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['logos'],
    'requires': [],
  },
]

#-------- HANDLER DICTIONARY ---------#
# dictionary of semi-permanent handlers so that I can keep one instance
# around between two hook functions
HANDLERS = {}
def addHandler(handler, key): HANDLERS[key] = handler
def getHandler(key): return HANDLERS[key]

#----------- LOGOS METADATA -----------#
LOGOS_MD_STRUCT = {
  'config': [
    '/distro/main/fullname/text()',
    '/distro/main/version/text()',
  ],
  'sources': [
    '//logos/path',
  ],
  'files': [
    'builddata/logos/',
  ]
}

#----------- MIXINS -------------#
class LogosOutputMixin:
    pass

#----------- INTERFACES -----------#
class LogosInterface(EventInterface, LocalsMixin, OutputEventMixin):
    def __init__(self, base):
        self.base = base
        EventInterface.__init__(self, self.base)
        LocalsMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' %(self.getBaseStore(),)),
                             self.base.IMPORT_DIRS)
        OutputEventMixin.__init__(self)

    def getMethod(self):
        method = self.base.config.get('//logos/@method', 'create')
        return method

class LogosHandler(OutputEventHandler):
    #
    # TODO: Add text formatting nodes' handling
    #
    def __init__(self, interface, data):
        self.cache_path = dirname(interface.getMetadata())
        self.logos_path = join(interface.getMetadata(), 'logos')
        self.mdfile = join(interface.getMetadata(), 'logos.md')
        self.locals = interface.locals        
        OutputEventHandler.__init__(self, interface.config, data, None, self.mdfile)
        self.controllist = {}        
        self.build_controllist()

    def build_controllist(self):
        logos = self.locals.getLocalPath(L_LOGOS, '/logos')
        for logo in logos.get('logo', fallback=[]):
            id = logo.attrib['id']
            install_path = logo.iget('location').text
            try:
                width = logo.iget('width').text
            except AttributeError:
                width = None
            try:
                height = logo.iget('height').text
            except AttributeError:
                height = None
            file_name = basename(id)
            dir_name = dirname(id)
            self.controllist[id] = {
                'install_path': install_path,
                'width': width,
                'height': height,
                'file_name': file_name,
                'dir_name': dir_name,
                }

    def read_metadata(self):
        """ 
        Read in self.mdfile and populate internal data structures:        
        * self.configvals : dictionary of configuration values keyed
                            off of their path in self.config                            
        * self.sources    : (basename, size, last modified time) tuples
                            of source images
        * self.files      : (basename, size, last modified time) tuples of
                            output images        
        Above data structures are only populated if self.data[x][0] is
        true, where x is one of 'config', sources', and 'files',
        respectively.  Sets self.mdvalid once read is complete.        
        """
        try:
            metadata = xmltree.read(self.mdfile)
        except ValueError:
            return # self.mdvalid not set
        
        # reset values
        self.configvals = {}
        self.sources = {}
        self.files = {}
        
        # set up self.configvals dictionary
        for item in self.data.get('config', []):
            try:
                node = metadata.get('/metadata/config-values/value[@path="%s"]' % item)[0]
                self.configvals[item] = node.text or NoneEntry(item)
            except IndexError:
                self.configvals[item] = NewEntry()
    
        # set up self.sources and self.files
        for key in ['sources', 'files']:
            object = getattr(self, key)
            for item in self.data[key]:
                sources = metadata.get('/metadata/%s/file' %(key,), fallback=[])
                for source in sources:
                    path = source.attrib['path']
                    size = source.iget('size').text
                    mtime = source.iget('lastModified').text
                    object[path] = (basename(path), size, mtime)
        self.mdvalid = True # md readin was successful

    def write_metadata(self):
        """ 
        Writes  metadata out to a file.   Converts the internal  data structures
        created in read_metadata(), above, into XML subtrees, assembles metadata
        tree  from  them,   and  writes  them  out  to  self.mdfile.    As  with 
        read_metadata(),  only  processes  the  elements  that  are  enabled  in
        self.data
        """
        if exists(self.mdfile):
            md = xmltree.read(self.mdfile)
            root = md.getroot()
        else:
            root = xmltree.Element('metadata')
            md = xmltree.XmlTree(root)
    
        # set up <config-values> element
        if self.data.has_key('config'):
            if not (self.configvalid and self.mdvalid):
                try: root.remove(root.get('/metadata/config-values', [])[0])
                except IndexError: pass
                configvals = xmltree.Element('config-values')
                root.insert(0, configvals)
                for path in self.data['config']:
                    try:
                        xmltree.Element('value', parent=configvals, text=self.config.get(path),
                                        attrs={'path': path})
                    except xmltree.XmlPathError:
                        xmltree.Element('value', parent=configvals, text=None, attrs={'path': path})
    
        # set up <sources> element
        if self.data.has_key('sources'):
            if not (self.sourcevalid and self.mdvalid):
                try: root.remove(root.get('/metadata/sources', [])[0])
                except IndexError: pass                
                source_node = xmltree.Element('sources', parent=root)
                for path in self.data['sources']:
                    for s_i in self.config.mget(path, []):
                        file_element = xmltree.Element('file', parent=source_node, text=None,
                                                       attrs={'path':s_i.text})
                        stat = os.stat(s_i)
                        size = xmltree.Element('size', parent=file_element, text=str(stat.st_size))
                        mtime = xmltree.Element('lastModified', parent=file_element,
                                                text=str(stat.st_mtime))

        # set up <files> element
        if self.data.has_key('files'):
            if not (self.filesvalid and self.mdvalid):
                try: root.remove(root.get('/metadata/files', [])[0])
                except IndexError: pass
                file_node = xmltree.Element('files', parent=root)
                for path in self.data['files']:
                    #
                    # if path is absolute path, joining it with self.logos_path
                    # has no effect.
                    #
                    path = join(self.cache_path, path)
                    for file in tree(path, prefix=True, dodirs=False, dofiles=True):
                        file_element = xmltree.Element('file', parent=file_node, text=None,
                                                       attrs={'path':file})
                        stat = os.stat(file)
                        size = xmltree.Element('size', parent=file_element, text=str(stat.st_size))
                        mtime = xmltree.Element('lastModified', parent=file_element,
                                                text=str(stat.st_mtime))
        md.write(self.mdfile)

    def initVars(self):
        pass

    def storeMetadata(self):
        self.write_metadata()
    
    def testInputChanged(self):
        if not self.mdvalid:
            return True
        else:
            self.configvalid = self._test_configvals_changed()
            self.filesvalid = self._test_files_changed()
            self.sourcevalid = self._test_source_changed()
            return (self.configvalid and self.filesvalid and \
                    self.sourcevalid and self.testInputValid())

    def testInputValid(self):        
        if not self.data.has_key('sources') or not hasattr(self, 'sources'):
            return False
        else:
            input_files = map(lambda x: self.sources[x][2], self.sources.keys())
            control_files = map(lambda x: self.controllist[x]['file_name'], self.controllist.keys())
            if not self._all_files_present(input_files, control_files):
                return False
            for path in self.sources.keys():
                id = self._get_path_id(self.sources[path][0])
                if not id:
                    return False                
                if not self._verify_file(path, self.controllist[id]):
                    return False
            return True
    
    def testOutputValid(self):
        if not self.data.has_key('files'):
            return False
        else:
            for path in self.files.keys():
                id = self._get_path_id(self.files[path][0])
                if not id:
                    return False
                filepath = join(self.cache_path, path)
                if not exists(filepath):
                    return False
                stats = os.stat(filepath)
                if (stats.st_mtime != self.files[path][2]) and \
                       (stats.st_size  != self.files[path][1]) and \
                       (self._verify_file(filepath, self.controllist[id])):
                    return False
            return True
    
    def removeObsoletes(self):
        pass
    
    def removeInvalids(self):
        pass
    
    def getInput(self):
        if not hasattr(self, 'sources'):
            return            
        for input_file in self.sources.keys():
            id = self._get_path_id(self.stores[input_file][0])
            if not id:
                self.interface.log(0, "file %s not found in the control list." %(input_file,))
                continue
            output_path = join(self.logos_path, self.controllist[id][dir_name])
            sync(input_file, output_path)

    def addOutput(self):
        if hasattr(self, 'sources') and self.sources:
            return
        for id in self.controllist.keys():
            if self.controllist[id]['width'] and self.controllist[id]['height']:
                file_name = join(self.logos_path, id)
                dir = dirname(file_name)
                mkdir(dir, parent=True)
                self._generate_image('TEST IMAGE', '/usr/share/fonts/bitstream-vera/VeraSe.ttf',
                                     50, file_name)
                                 
    def _generate_image(self, text, font, font_size, file_name, fmt='png'):
        """Generate a captcha image"""
        import random
        #
        # randomly select the foreground color
        #
        fgcolor = random.randint(0,0xffff00)
        #
        # make the background color the opposite of fgcolor
        #
        bgcolor = fgcolor ^ 0xffffff
        #
        # create a font object
        #
        font = ImageFont.truetype(font, font_size)
        #
        # determine dimensions of the text
        #
        dim = font.getsize(text)
        #
        # create a new image slightly larger that the text
        #
        im = Image.new('RGB', (dim[0]+50,dim[1]+50), bgcolor)
        d = ImageDraw.Draw(im)
        d.text((15, 45), text, font=font, fill=fgcolor)
        im = im.filter(ImageFilter.EDGE_ENHANCE_MORE)
        #
        # save the image to a file
        #
        im.save(file_name, format=fmt)        
        
    def _get_path_id(self, filename):
        for item in self.controllist.keys():
            if self.controllist[item]['file_name'] == filename:
                return item
        return None        

    def _verify_file(self, input, control):
        try:
            width = int(control['width'])
        except ValueError:
            width = None
        try:
            height = int(control['height'])
        except ValueError:
            height = None
        if width and height:
            control_size = (width, height)
            try:
                image = Image.open(input)
            except IOError:
                return False
            input_size = image.size
            if input_size != control_size:
                return False
        return True
        
    def _all_files_present(self, input, control):
        input.sort()
        control.sort()
        return input == control

    def _test_files_changed(self):
        if not self.data.has_key('files'):
            return True
        else:
            return self.__files_touched(self.data['files'], self.files)
        
    def _test_source_changed(self):
        if not self.data.has_key('sources'):
            return True
        else:
            return self.__files_touched(self.data['sources'], self.sources)

    def __files_touched(self, files, control):
        input = {}
        for path in files:
            path = join(self.cache_path, path)
            for file in tree(path, prefix=True, dodirs=False, dofiles=True):
                stat = os.stat(file)
                size = stat.st_size
                mtime = stat.st_mtime
                input[file] = (size, mtime)
        return (input != control)

#---------- HOOK FUNCTIONS -----------#  
def init_hook(interface):
    parser = interface.getOptParser('build')
    parser.add_option('--with-logos',
                      default=None,
                      dest='with_logos',
                      metavar='LOGOSDIR',
                      help='use the logos found in LOGOSDIR instead of generating them')
    
def prelogos_hook(interface):
    handler = LogosHandler(interface, LOGOS_MD_STRUCT)
    addHandler(handler, 'logos')
    interface.disableEvent('logos')
    #
    # We need to run the logos hook when the test input has changed or the input
    # files are invalid.
    #
    if interface.getMethod() != 'none':
        interface.log(0, "processing logos")
        interface.log(1, "the logos method is not 'none'")
        if handler.testInputChanged():
            interface.log(1, "the input files have changed")
            handler.removeObsoletes()
            interface.enableEvent('logos')
        else:
            if not handler.testOutputValid():
                interface.log(1, "the output is not valid")
                handler.removeInvalids()
                interface.enableEvent('logos')
    if (interface.eventForceStatus('logos') or False):
        interface.enableEvent('logos')
    interface.setFlag('logos', False)
        
def logos_hook(interface):
    handler = getHandler('logos')
    interface.modify(handler)
    
def postlogos_hook(interface): 
    if interface.getMethod() != 'none':
        interface.setFlag('logos', True)        




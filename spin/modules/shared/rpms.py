from ConfigParser import ConfigParser

import colorsys
import re

from rendition import mkrpm
from rendition import pps
from rendition import xmllib

from spin.event   import Event
from spin.logging import L1

try:
  import Image
  import ImageDraw
except ImportError:
  raise ImportError("missing 'python-imaging' module")

__all__ = ['InputFilesMixin', 'RpmBuildMixin', 'ImagesGenerator']

P = pps.Path

VER_X_REGEX = re.compile('[^0-9]*([0-9]+).*')

class InputFilesMixin:
  """
  Mixin that can be used to setup the download and get list of data
  files that are sync'd.
  """
  def __init__(self, install_info):
    self.install_info = install_info
    self.ids = set()

  def _setup_download(self):
    for k,v in self.install_info.items():
      xpath, dst, mode, absolute = v

      if xpath and self.config.pathexists(xpath):
        default_dir = P(dst) / P(self.config.get(xpath).getparent().get('@dest', ''))
        for item in self.config.xpath(xpath, []):
          s,d,f,m = self.io._process_path_xml(item, relpath=default_dir,
                                             absolute=absolute, mode=mode)
          if isinstance(s, pps.path.file.FilePath): #! bad, see event/fileio.py
            s = self._config.file.dirname / s

          id = self._get_download_id(k)
          self.ids.add(id)

          self.io.add_item(s, self.build_folder//d/f, id=id or s, mode=m)

          attribs = []
          for attr in item.attrib:
            attribs.append(attr)
          self._handle_attributes(id, item, attribs)

  def _get_download_id(self, type):
    return type

  def _handle_attributes(self, id, item, attribs):
    pass

class RpmBuildMixin:
  def __init__(self, rpm_name, rpm_desc, rpm_summary, rpm_license=None,
               default_provides=None, default_obsoletes=None, default_requires=None,
               packagereq_type='mandatory', packagereq_default=None,
               packagereq_requires=None):
    self.rpm_desc = rpm_desc
    self.rpm_name = rpm_name
    self.rpm_summary = rpm_summary
    self.rpm_license = rpm_license

    self.default_obsoletes = default_obsoletes or []
    self.default_provides = default_provides or []
    self.default_requires = default_requires or []

    self.packagereq_type = packagereq_type
    self.packagereq_default = packagereq_default
    self.packagereq_requires = packagereq_requires

    self.autofile = P(self._config.file + '.dat')

    # RPM build variables
    self.build_folder = self.mddir / 'build'
    self.bdist_base = self.mddir / 'rpm-base'
    self.rpm_base = self.bdist_base / 'rpm'
    self.dist_dir = self.bdist_base / 'dist'

    self.rpm_obsoletes = None
    self.rpm_provides = None
    self.rpm_requires = None

  #---------------- EVENT METHODS -----------------#
  def check(self):
    return self.rpm_release == '0' or \
           not self.autofile.exists() or \
           self.diff.test_diffs()

  def setup(self):
    self._setup_build()

  def run(self):
    self.io.clean_eventcache(all=True)

    self._check_release()

    self.build_folder.mkdirs()
    self._generate()
    self._write_spec()
    self._write_manifest()

    self.log(1, L1("building %s-%s-%s.%s.rpm" % \
                   (self.rpm_name, self.rpm_version, self.rpm_release, self.rpm_arch)))
    mkrpm.build(self.build_folder, self.mddir, createrepo=False,
                bdist_base=self.bdist_base, rpm_base=self.rpm_base,
                dist_dir=self.dist_dir, keep_source=True,
                quiet=(self.logger.threshold < 5))

    self._save_release()

    self.DATA['output'].append(self.rpm_path)
    self.DATA['output'].append(self.srpm_path)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    custom_rpm_data = {}

    custom_rpm_data['packagereq-default'] = self.packagereq_default
    custom_rpm_data['packagereq-requires'] = self.packagereq_requires
    custom_rpm_data['packagereq-type'] = self.packagereq_type

    custom_rpm_data['rpm-name'] = self.rpm_name
    custom_rpm_data['rpm-obsoletes'] = self.rpm_obsoletes
    custom_rpm_data['rpm-provides'] = self.rpm_provides
    custom_rpm_data['rpm-requires'] = self.rpm_requires

    custom_rpm_data['rpm-path'] = self.rpm_path
    custom_rpm_data['srpm-path'] = self.srpm_path

    self.cvars['custom-rpms-data'][self.id] = custom_rpm_data

  def verify_rpm_exists(self):
    "rpm exists"
    self.verifier.failUnless(self.rpm_path.exists(),
                             "unable to find rpm at '%s'" % str(self.rpm_path))

  def verify_srpm_exists(self):
    "srpm exists"
    self.verifier.failUnless(self.srpm_path.exists(),
                             "unable to find srpm at '%s'" % str(self.srpm_path))

  #------------- PROPERTIES --------------#
  def _get_rpm_path(self):
    return self.mddir/'RPMS/%s-%s-%s.%s.rpm' % \
           (self.rpm_name, self.rpm_version, self.rpm_release, self.rpm_arch)
  rpm_path = property(_get_rpm_path)

  def _get_srpm_path(self):
    return self.mddir/'SRPMS/%s-%s-%s.src.rpm' % \
           (self.rpm_name, self.rpm_version, self.rpm_release)
  srpm_path = property(_get_srpm_path)

  def _get_data_files(self):
    data_files = {}
    for item in self.build_folder.findpaths(type=pps.constants.TYPE_DIR, mindepth=1):
      files = item.findpaths(type=pps.constants.TYPE_NOT_DIR,
                             mindepth=1, maxdepth=1)
      if files:
        data_files.setdefault(P(item[len(self.build_folder):]), []).extend(files)
    return data_files
  data_files = property(_get_data_files)

  #--------- RPM BUILD HELPER METHODS ---------#
  def _setup_build(self, **kwargs):
    if self.autofile.exists():
      self.rpm_release = xmllib.config.read(self.autofile).get(
       '/distro/%s/rpms/%s/release/text()' % (self.pva, self.id), '0')
    else:
      self.rpm_release = '0'

    if self.config.get('@use-default-set', 'True'):
      self.rpm_obsoletes = self.default_obsoletes
    else:
      self.rpm_obsoletes = []
    if self.config.pathexists('obsoletes/text()'):
      self.rpm_obsoletes.extend(self.config.xpath('obsoletes/text()', []))
    if kwargs.has_key('obsoletes'):
      self.rpm_obsoletes.extend(kwargs['obsoletes'])

    self.rpm_provides = [ x for x in self.rpm_obsoletes ]
    if self.default_provides:
      self.rpm_provides.extend(self.default_provides)
    if kwargs.has_key('provides'):
      self.rpm_provides.extend(kwargs['provides'])

    if self.default_requires:
      self.rpm_requires = self.default_requires
    else:
      self.rpm_requires = []
    if self.config.pathexists('requires/text()'):
      self.rpm_requires.extend(self.config.xpath('requires/text()', []))
    if kwargs.has_key('requires'):
      self.rpm_requires.extend(kwargs['requires'])

    self.diff.setup(self.DATA)

    self.rpm_arch = kwargs.get('arch', 'noarch')
    self.rpm_author = kwargs.get('author', 'spin')
    self.rpm_fullname = kwargs.get('fullname', self.fullname)
    if kwargs.has_key('version'):
      self.rpm_version = kwargs['version']
    else:
      vermatch = VER_X_REGEX.match(self.version)
      if vermatch:
        self.rpm_version = vermatch.group(1)
      else:
        raise ValueError("Invalid version string; must contain at least one integer")

  def _save_release(self):
    if self.autofile.exists():
      root_element = xmllib.config.read(self.autofile).get('/distro')
    else:
      root_element = xmllib.config.Element('distro')

    pva_element = xmllib.config.uElement(self.pva, parent=root_element)
    rpms_element = xmllib.config.uElement('rpms', parent=pva_element)
    parent_element = xmllib.config.uElement(self.id, parent=rpms_element)
    release_element = xmllib.config.uElement('release', parent=parent_element)

    release_element.text = self.rpm_release
    root_element.write(self.autofile)

    if self._config.file.exists():
      # set the mode and ownership of distro.conf.dat and distro.conf to
      # be the same.
      stat = self._config.file.stat()
      self.autofile.chown(stat.st_uid, stat.st_gid)
      self.autofile.chmod(stat.st_mode)

  def _check_release(self):
    if self.rpm_release == '0' or  \
           not self.autofile.exists() or \
           not self.mdfile.exists() or \
           self.diff.has_changed('input') or \
           self.diff.has_changed('variables') or \
           self.diff.has_changed('config'):
      self.rpm_release = str(int(self.rpm_release)+1)

  def _write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'

    spec = ConfigParser()
    spec.add_section('pkg_data')
    spec.add_section('bdist_rpm')

    spec.set('pkg_data', 'name', self.rpm_name)
    spec.set('pkg_data', 'long_description', self.rpm_desc)
    spec.set('pkg_data', 'description', self.rpm_summary)
    spec.set('pkg_data', 'author', self.rpm_author)
    spec.set('pkg_data', 'version', self.rpm_version)

    if self.rpm_license is not None:
      spec.set('pkg_data', 'license', self.rpm_license)

    spec.set('bdist_rpm', 'force_arch', self.rpm_arch)
    spec.set('bdist_rpm', 'distribution_name', self.rpm_fullname)

    spec.set('bdist_rpm', 'release', self.rpm_release)

    if self.rpm_provides:
      spec.set('bdist_rpm', 'provides',  ' '.join(self.rpm_provides))
    if self.rpm_requires:
      spec.set('bdist_rpm', 'requires',  ' '.join(self.rpm_requires))
    if self.rpm_obsoletes:
      spec.set('bdist_rpm', 'obsoletes', ' '.join(self.rpm_obsoletes))

    build_script = self._get_build_script()
    if build_script:
      spec.set('bdist_rpm', 'build_script', build_script)

    clean_script = self._get_clean_script()
    if clean_script:
      spec.set('bdist_rpm', 'clean_script', clean_script)

    install_script = self._get_install_script()
    if install_script:
      spec.set('bdist_rpm', 'install_script', install_script)

    post_install_script = self._get_post_install_script()
    if post_install_script:
      spec.set('bdist_rpm', 'post_install', post_install_script)

    pre_uninstall_script = self._get_pre_uninstall_script()
    if pre_uninstall_script:
      spec.set('bdist_rpm', 'pre_uninstall', pre_uninstall_script)

    post_uninstall_script = self._get_post_uninstall_script()
    if post_uninstall_script:
      spec.set('bdist_rpm', 'post_uninstall', post_uninstall_script)

    verify_script = self._get_verify_script()
    if verify_script:
      spec.set('bdist_rpm', 'verify_script', verify_script)

    triggerin = self._get_triggerin()
    if triggerin:
      spec.set('bdist_rpm', 'triggerin', '\n\t'.join(triggerin))

    triggerun = self._get_triggerun()
    if triggerun:
      spec.set('bdist_rpm', 'triggerun', '\n\t'.join(triggerun))

    triggerpostun = self._get_triggerpostun()
    if triggerpostun:
      spec.set('bdist_rpm', 'triggerpostun', '\n\t'.join(triggerpostun))

    ghost_files = self._get_ghost_files()
    if ghost_files:
      spec.set('bdist_rpm', 'ghost_files', '\n\t'.join(ghost_files))

    self._add_data_files(spec)
    self._add_config_files(spec)
    self._add_doc_files(spec)

    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def _write_manifest(self):
    manifest = ['setup.py']
    manifest.extend( [ x.tokens[len(self.build_folder.tokens):] \
                       for x in self.build_folder.findpaths(type=pps.constants.TYPE_NOT_DIR) ] )
    (self.build_folder/'MANIFEST').write_lines(manifest)

  def _add_data_files(self, spec):
    data_files = []
    for installdir, files in self.data_files.items():
      data_files.append('%s : %s' %(installdir, ', '.join(files)))
    if data_files:
      spec.set('pkg_data', 'data_files', '\n\t'.join(data_files))

  def _add_config_files(self, spec):
    config_files = []
    for installdir in self.data_files.keys():
      if installdir.startswith('/etc'): # config files
        config_files.extend([
          installdir/x.basename for x in self.data_files[installdir]
        ])
    if config_files:
      spec.set('bdist_rpm', 'config_files', '\n\t'.join(config_files))

  def _add_doc_files(self, spec):
    doc_files = []
    if (self.build_folder / 'COPYING').exists():
      doc_files.append('COPYING')
    for installdir in self.data_files.keys():
      if installdir.startswith('/usr/share/doc'):
        doc_files.extend([
          installdir/x.basename for x in self.data_files[installdir]
        ])
    if doc_files:
      spec.set('bdist_rpm', 'doc_files', '\n\t'.join(doc_files))

  #----------- OPTIONAL METHODS --------#
  def _generate(self):
    pass

  def _get_ghost_files(self):
    return None

  def _get_build_script(self):
    return None
  def _get_clean_script(self):
    return None
  def _get_install_script(self):
    return None
  def _get_post_install_script(self):
    return None
  def _get_post_uninstall_script(self):
    return None
  def _get_pre_install_script(self):
    return None
  def _get_pre_uninstall_script(self):
    return None
  def _get_prep_script(self):
    return None
  def _get_verify_script(self):
    return None

  def _get_triggerin(self):
    return None
  def _get_triggerun(self):
    return None
  def _get_triggerpostun(self):
    return None

class ImagesGenerator(object):
  def __init__(self):
    self.images_dir = None

  def _setup_image_creation(self, shared_dir):
    found_images_dir = False
    for path in self.SHARE_DIRS:
      images_dir = path / shared_dir
      if images_dir.exists() and self.images_dir is None:
        self.images_dir = images_dir
        found_images_dir = True
    if not found_images_dir:
      raise RuntimeError("Unable to find %s/ directory in share path(s) '%s'" % \
                         (shared_dir, self.SHARE_DIRS))

    fullname = self.cvars['base-info']['fullname']
    version = self.cvars['base-info']['version']
    try:
      self.hue_info = HUE_INFO[fullname][version]
    except KeyError:
      # See if the version of the input distribution is a bugfix
      # version, and if it is, use the hue difference for the main
      # release.
      found = False
      if HUE_INFO.has_key(fullname):
        for ver in HUE_INFO[fullname]:
          if version.startswith(ver):
            found = True
            self.hue_info = HUE_INFO[fullname][ver]
            break
      if not found:
        self.hue_info = HUE_INFO['*']['0']

  def _copy_static_images(self):
    for src in self.images_dir.findpaths(type=pps.constants.TYPE_NOT_DIR):
      dst = self.build_folder / src.relpathfrom(self.images_dir)
      dst.dirname.mkdirs()
      self.link(src, dst.dirname)

  def _create_dynamic_images(self, image_locals):
    self.base_image = self._create_base_image('baseimage.png')

    for file_name in image_locals:
      properties = image_locals[file_name]
      output_locations = properties.get('output_locations', [file_name])
      for location in output_locations:
        self._create_image(
          self.build_folder // location,
          properties['width'],
          properties['height'],
          properties['format'],
          strings = properties.get('strings', None),
          base_image = properties.get('base_image', None)
        )

    self.base_image = None

  def _create_image(self, file_name, width, height, format,
                    strings=None, base_image=None):
    if base_image is not None:
      img = self._create_base_image(base_image)
      img.resize((width, height), Image.ANTIALIAS)
    else:
      img = self.base_image.resize((width, height), Image.ANTIALIAS)

    if strings:
      for i in strings:
        text_string    = i.get('text', '') % self.cvars['distro-info']
        halign         = i.get('halign', 'center')
        text_coords    = i.get('text_coords', (img.size[0]/2, img.size[1]/2))
        text_max_width = i.get('text_max_width', img.size[0])
        font_color     = i.get('font_color', 'black')
        font_size      = i.get('font_size', 52)
        font_size_min  = i.get('font_size_min', None)
        font_path      = self._get_font_path(i.get('font',
                                                   'DejaVuLGCSans.ttf'))
        draw, handler = ImageDraw.getdraw(img)
        while True:
          font = handler.Font(font_color, font_path, size=font_size)
          w, h = draw.textsize(text_string, font)
          if w <= (text_max_width or im.size[0]):
            break
          else:
            font_size -= 1
          if font_size < (font_size_min or font_size):
            break

        if halign == 'center':
          draw.text((text_coords[0]-(w/2), text_coords[1]-(h/2)),
                    text_string, font)
        elif halign == 'right':
          draw.text((text_coords[0]-w, text_coords[1]-(h/2)),
                    text_string, font)

    file_name.dirname.mkdirs()
    img.save(file_name, format=format)

  def _get_font_path(self, font):
    """
    Given a font file name, returns the full path to the font located in one
    of the share directories
    """
    for path in self.SHARE_DIRS:
      available_fonts = (path/'fonts').findpaths(glob=font)
      if available_fonts:
        font_path = available_fonts[0]; break
      if not font_path:
        raise RuntimeError("Unable to find font file '%s' in share path(s) "
                           "'%s'" %  font_path, self.SHARE_DIRS)
    return font_path

  def _create_base_image(self, file_name):
    input_image = None
    for path in self.SHARE_DIRS:
      input_image = path / 'static' / file_name
      if input_image.exists():
        break
      else:
        input_image = None
    if input_image is None:
      raise RuntimeError("Unable to find static base image '%s' in share path(s) '%s'" % \
                         (file_name, self.SHARE_DIRS))

    img = Image.open(input_image)
    imo = Image.new(img.mode, img.size)

    color_mapping = {}
    input = img.getdata()
    output = []
    for rgba in input:
      if not color_mapping.has_key(rgba):
        h, s, v = self._rgb_to_hsv(*rgba[:3])
        h = self.hue_info / 360.
        r, g, b = self._hsv_to_rgb(h, s, v)

        # maintain RGBA-ness, if input image mode is RGBA
        color_mapping[rgba] = (r, g, b) + tuple(rgba[3:])

      new_rgba = color_mapping[rgba]
      output.append(new_rgba)

    imo.putdata(output)
    return imo

  def _rgb_to_hsv(self, r, g, b):
    return colorsys.rgb_to_hsv(r/255., g/255., b/255.)

  def _hsv_to_rgb(self, h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r*255), int(g*255), int(b*255)

#---------- GLOBAL VARIABLES --------#
# each element for a distro's version, e.g. redhat/5, maps to the difference to the
# hue of the base image in the shared folder.
HUE_INFO = {
  'CentOS': {
    '5': 213,
  },
  'Fedora Core': {
    '6': 212,
  },
  'Fedora': {
    '7': 220,
    '8': 205,
  },
  'Red Hat Enterprise Linux Server': {
    '5': 0,
  },
  '*': {
    '0': 0,
  }
}

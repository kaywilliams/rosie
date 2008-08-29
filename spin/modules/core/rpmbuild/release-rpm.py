#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
from rendition import pps

from spin.event import Event

from spin.modules.shared import RpmBuildMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ReleaseRpmEvent'],
  description = 'creates a release RPM',
  group       = 'rpmbuild',
)

class ReleaseRpmEvent(RpmBuildMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'release-rpm',
      parentid = 'rpmbuild',
      version = '0.91',
      requires = ['release-versions', 'input-repos'],
      provides = ['rpmbuild-data'],
    )

    RpmBuildMixin.__init__(self,
      '%s-release' % self.name,
      '%s release files created by spin' % self.fullname,
      '%s release files' % self.name,
      obsoletes = ['fedora-release', 'redhat-release', 'centos-release',
                   'fedora-release-notes', 'redhat-release-notes', 'centos-release-notes']
    )

    d = self.rpm.source_folder
    self.filetypes = {
      'eula'    : d/'usr/share/eula',
      'html'    : d/'usr/share/doc/HTML',
      'doc'     : d/'usr/share/doc/%s-release-notes-%s' % (self.name, self.version),
      'release' : d/'usr/share/doc/%s-release-%s' % (self.name, self.version),
      'etc'     : d/'etc',
      'eulapy'  : d/'usr/share/firstboot/modules',
    }

    self.DATA = {
      'config':    ['.'],
      'variables': ['fullname', 'name', 'rpm.release',
                    'cvars[\'release-versions\']'],
      'input':     [],
      'output':    [self.rpm.build_folder],
    }

  def setup(self):
    obsoletes = [ '%s %s %s' % (n,e,v)
                  for n,e,v in self.cvars.get('release-versions', [])]
    provides  = [ '%s %s %s' % (n,e,v)
                  for n,e,v in self.cvars.get('release-versions', [])]
    provides.extend( [ 'redhat-release %s %s' % (e,v)
                       for _,e,v in self.cvars.get('release-versions', [])])
    self.rpm.setup_build(obsoletes=obsoletes, provides=provides)

    self.io.add_xpath('eula',  self.filetypes['eula'])
    self.io.add_xpath('html',  self.filetypes['html'])
    self.io.add_xpath('doc',   self.filetypes['doc'])
    self.io.add_xpath('files', self.filetypes['release'])

    # eulapy file
    if ( self.config.getbool('eula/@include-in-firstboot', 'True') and
         self.config.pathexists('eula') ):
      found = False
      for path in self.SHARE_DIRS:
        path = path/'release/eula.py'
        if path.exists():
          self.io.add_fpath(path, self.filetypes['eulapy'])
          found = True; break
      if not found:
        raise RuntimeError("release/eula.py not found in %s" % ', '.join(self.SHARE_DIRS))

  def generate(self):
    "Generate additional files."
    RpmBuildMixin.generate(self)

    self.io.sync_input(cache=True)
    for filetype,dir in self.filetypes.items():
      generator = '_generate_%s_files' % filetype
      if hasattr(self, generator):
        getattr(self, generator)(dir)
    self._verify_release_notes()

  def _verify_release_notes(self):
    "Ensure the presence of RELEASE-NOTES.html and an index.html"
    rnotes = self.rpm.source_folder.findpaths(glob='RELEASE-NOTES*')
    if len(rnotes) == 0:
      self.filetypes['html'].mkdirs()

      # create a default release notes file because none were found.
      import locale
      path = self.filetypes['html']/'RELEASE-NOTES-%s.html' % \
        locale.getdefaultlocale()[0]

      f = path.open('w')
      f.write(self.locals.L_RELEASE_HTML)
      f.close()
      path.chmod(0644)

      index_html = self.filetypes['html']/'index.html'
      if not index_html.exists():
        path.link(index_html)
        index_html.chmod(0644)

  def _generate_etc_files(self, dest):
    dest.mkdirs()
    release_string = ['%s %s' % (self.fullname, self.version)]
    issue_string = ['Kernel \\r on an \\m\n']

    # write the appliance-release and redhat-release files
    (dest/'redhat-release').write_lines(release_string)
    (dest/'%s-release' % self.name).write_lines(release_string)

    # write the issue and issue.net files
    (dest/'issue').write_lines(release_string + issue_string)
    (dest/'issue.net').write_lines(release_string + issue_string)

    (dest/'redhat-release').chmod(0644)
    (dest/'%s-release' % self.name).chmod(0644)
    (dest/'issue').chmod(0644)
    (dest/'issue.net').chmod(0644)

#
# Copyright (c) 2015
# Deploy Foundation. All rights reserved.
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
import copy 
import re

from deploy.errors   import (DeployEventError, MissingIdError,
                             DuplicateIdsError, ConfigError)
from deploy.event    import Event, CLASS_META
from deploy.util     import pps

from deploy.modules.shared import (MkrpmRpmBuildMixin,
                                   RepoSetupEventMixin,
                                   Trigger, 
                                   TriggerContainer)

from deploy.util.rxml.tree import MACRO_REGEX


def make_config_rpm_events(ptr, modname, element_name, globals):
  config_rpm_elems = getattr(ptr, 'cvars[\'config-rpm-elems\']', {})
  new_events = []
  xpath   = '/*/%s/%s' % (modname, element_name)

  # create event classes based on user configuration
  for config in ptr.definition.xpath(xpath, []):

    # convert user provided id to a valid class name
    rpmid = config.getxpath('@id', None)
    if rpmid == None: 
      raise MissingIdError(config)
    name = re.sub('[^0-9a-zA-Z_]', '', rpmid).capitalize()
    setup_name = '%sConfigRpmSetupEvent' % name
    base_name = '%sConfigRpmEvent' % name

    # get config path and rpmid
    config_base = '%s[@id="%s"]' % (xpath, rpmid)

    # check for dups
    if rpmid in config_rpm_elems:
      if config == config_rpm_elems[rpmid]:
        continue # elem exactly matches a previous elem, ignore
      else:
        raise DuplicateIdsError(ptr.definition.xpath('%s[@id="%s"]'
                                                      % (xpath, rpmid)))

    # create new classes
    exec """%s = config.ConfigRpmSetupEvent('%s', 
                         (config.ConfigRpmSetupEventMixin,), 
                         { 'rpmid'      : '%s',
                           'config_base': '%s',
                           '__init__'   : config.init_config_setup_event,
                         }
                        )""" % (
                        setup_name, setup_name, rpmid, config_base) in globals

    exec """%s = config.ConfigRpmEvent('%s', 
                         (config.ConfigRpmEventMixin,), 
                         { 'rpmid'      : '%s',
                           'config_base': '%s',
                           '__init__'   : config.init_config_event,
                         }
                        )""" % (
                        base_name, base_name, rpmid, config_base) in globals

    # update lists with new classname
    config_rpm_elems[rpmid] = config 
    for name in [setup_name, base_name]:
      new_events.append(name)

  # update cvars rpm-event-ids
  ptr.cvars['config-rpm-elems'] = config_rpm_elems

  return new_events

class ConfigRpmSetupEventMixin(RepoSetupEventMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-rpm-setup' % self.rpmid,
      parentid = 'config-rpms-setup',
      ptr = ptr,
      version = 1.00,
      provides = ['config-rpm-setup'],
      config_base = self.config_base,
      suppress_run_message = True,
    )

    self.DATA = {
      'input':     set(),
      'config':    set(),
      'variables': set(),
      'output':    set(),
    }

    RepoSetupEventMixin.__init__(self)


class ConfigRpmEventMixin(MkrpmRpmBuildMixin): 
  config_mixin_version = "1.05"

  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-rpm' % self.rpmid,
      parentid = 'config-rpms',
      ptr = ptr,
      version = 1.00,
      provides = ['config-rpm'],
      config_base = self.config_base,
    )
 
    # Add rpm requires, provides and obsoletes to event. This allows event
    # ordering to mimic rpm ordering. Needed for prep scripts (in 
    # ConfigRpmSetupEventMixin) to provide content for use for later rpms, and
    # may as well have setup and main events follow the same order.
    self.conditionally_requires.update(
      ['%s-rpm' % x for x in self.config.xpath('./requires/text()', [])])
    self.provides.update(
      ['%s-rpm' % x for x in self.config.xpath('./provides/text()', [])])
    self.provides.update(
      ['%s-rpm' % x for x in self.config.xpath('./obsoletes/text()', [])])

    self.conditionally_requires.add('packages')
    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'input':     set(),
      'config':    set(['.']),
      'variables': set(),
      'output':    set(),
    }

    MkrpmRpmBuildMixin.__init__(self)

  def validate(self):
    self.io.validate_destnames([ path for path in 
      self.config.xpath(('files'), [] ) ])

    for elem in self.config.xpath('*[name()="script" or name()="trigger"]', []):
      text = copy.deepcopy(elem.text)

      # error on empty content
      if not text:
        raise EmptyScriptContentError(elem)

      # rpmbuild behaves badly with unclosed macros in scripts, resulting in a
      # confusing error about installed but unpackaged files (which occurs
      # because rpmbuild fails to find the %files element)
      count = 0 
      while True:
        inner_macros = re.findall(MACRO_REGEX, text)
        for macro in inner_macros:
          count += 1
          text = text.replace(macro, '', 1)
        if not inner_macros:
          break

      if not count == elem.text.count('%{'):
        raise InvalidMacroError(elem)

  def setup(self, **kwargs):
    self.diff.setup(self.DATA)

    self.DATA['variables'].add('config_mixin_version')

    desc = self.config.getxpath('description/text()', 
       "The %s package provides configuration files and scripts for "
       "the %s repository." % (self.rpmid, self.fullname))
    summary = self.config.getxpath('summary/text()', self.rpmid) 
    license = self.config.getxpath('license/text()', 'GPLv2')

    MkrpmRpmBuildMixin.setup(self, name=self.rpmid, desc=desc, summary=summary, 
                             license=license, 
                             requires = ['coreutils', 'diffutils', 'findutils',
                                         'grep', 'sed'])


    # add files for synchronization to the build folder
    self.io.add_xpath('files', self.srcfiledir, allow_text=True) 

    # add triggers for synchronization to scripts folder
    for script in self.config.xpath('trigger', []):
      self.io.add_xpath(self._config.getroottree().getpath(script),
                        self.scriptdir, destname='%s-%s' % (
                        script.getxpath('@type'), script.getxpath('@trigger')),
                        content='text', allow_text=True,
                        id='triggers')

  def run(self):
    MkrpmRpmBuildMixin.run(self)

  def apply(self):
    MkrpmRpmBuildMixin.apply(self)
    self.cvars.setdefault('config-rpms', []).append(self.rpminfo['name'])

# ------ Metaclass for creating Config RPM Events -------- #
class ConfigRpmSetupEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)

class ConfigRpmEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)


# -------- Error Classes --------#
class EmptyScriptContentError(ConfigError):
  def __init__(self, elem):
    ConfigError.__init__(self, elem)

  def __str__(self):
    return ("Validation Error: the following element has no content:\n%s"
            % self.errstr)

class InvalidMacroError(ConfigError):
  def __init__(self, elem):
    ConfigError.__init__(self, elem, full=True)

  def __str__(self):
    return ("Validation Error: the following element contains a macro "
            "placeholder with unbalanced braces '%%{}':\n%s"
            % self.errstr)

# -------- init methods called by new_rpm_events -------- #
def init_config_setup_event(self, ptr, *args, **kwargs):
  ConfigRpmSetupEventMixin.__init__(self, ptr, *args, **kwargs)

def init_config_event(self, ptr, *args, **kwargs):
  ConfigRpmEventMixin.__init__(self, ptr, *args, **kwargs)

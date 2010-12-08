import ConfigParser
import StringIO

from systemstudio.util.repo.repo import *

def ReposFromXml(tree, cls=BaseRepo, original=None):
  """Create Repo objects from an XmlTree <repo> elements, or update values
  of existing repos."""
  repos = RepoContainer()
  repos.update(original or {})

  for repoxml in tree.getchildren():
    if repoxml.tag != 'repo': continue
    kwargs = {'id': repoxml.get('@id')}
    for attr in set([ i.tag for i in repoxml.getchildren() ]):
      # join together elements if they occur more than one time
      kwargs[attr] = ' '.join(repoxml.xpath('%s/text()' % attr, [])).strip()
    repos.add_repo(cls(**kwargs))

  return repos

def ReposFromString(s, cls=BaseRepo, original=None):
  "Create Repo objects from a string"
  try:
    return _ReposFromFileObject(StringIO.StringIO(s), cls=cls, original=original)
  except ConfigParser.Error, e:
    raise RepoStringParseError(str(e))

def ReposFromFile(f, cls=BaseRepo, original=None):
  "Create Repo objects from a file"
  try:
    return _ReposFromFileObject(open(str(f)), cls=cls, original=original)
  except ConfigParser.Error, e:
    raise RepoFileParseError(str(e), f)

def _ReposFromFileObject(fo, cls=BaseRepo, original=None):
  cp = ConfigParser.ConfigParser()
  cp.readfp(fo)

  repos = RepoContainer()
  repos.update(original or {})

  for id in cp.sections():
    if id == 'main': continue # skip the [main] section
    kwargs = {'id':id}
    for option in cp.options(id):
      kwargs[option] = cp.get(id, option).strip()
    repos.add_repo(cls(**kwargs))
  return repos

from defaults import * # imported last to avoid circular ref

class RepoFileParseError(Exception):
  def __str__(self):
    return 'Error parsing repo file \'%s\'; error was:\n%s' \
           % (self.args[1], self.args[0])

class RepoStringParseError(Exception):
  def __str__(self):
    return 'Error parsing repo string; error was:\n%s' % self.args[0]

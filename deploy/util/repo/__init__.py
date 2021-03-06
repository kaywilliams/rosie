import ConfigParser
import StringIO

from deploy.util.repo.repo import *

def ReposFromXml(tree, cls=BaseRepo, original=None, 
                 ignore_duplicates=False, **kwargs):
  """Create Repo objects from an XmlTree <repo> elements, or update values
  of existing repos."""
  repos = RepoContainer()
  repos.update(original or {})
  for repoxml in tree.getchildren():
    if repoxml.tag != 'repo': continue
    args = kwargs.copy()
    args['id'] =  repoxml.getxpath('@id')
    for attr in set([ i.tag for i in repoxml.getchildren() ]):
      if attr in [ 'gpgkey', 'baseurl', 'mirrorlist',
                   'sslcacert', 'sslclientkey', 'sslclientcert' ]:
        # use rxml.config getpath to provide correctly resolved paths, then
        # join the results of multiple elements with the same name
        args[attr] = ' '.join(tree.getpaths('%s/%s/text()'
          % (tree.getroottree().getpath(repoxml), attr), [])).strip()
      else:
        # just join the results of multiple elements with the same name
        args[attr] = ' '.join(repoxml.xpath('%s/text()' % attr, [])).strip()
    repos.add_repo(cls(**args), 
                   ignore_duplicates=ignore_duplicates)

  return repos

def ReposFromString(s, cls=BaseRepo, original=None, 
                    ignore_duplicates=False, **kwargs):
  "Create Repo objects from a string"
  try:
    return _ReposFromFileObject(StringIO.StringIO(s), cls=cls, 
                original=original, 
                ignore_duplicates=ignore_duplicates, **kwargs)
  except ConfigParser.Error, e:
    raise RepoStringParseError(str(e))

def ReposFromFile(f, cls=BaseRepo, original=None, **kwargs):

  "Create Repo objects from a file"
  try:
    return _ReposFromFileObject(open(str(f)), cls=cls, original=original,
                                **kwargs)
  except ConfigParser.Error, e:
    raise RepoFileParseError(str(e), f)

def _ReposFromFileObject(fo, cls=BaseRepo, original=None, 
                         ignore_duplicates=False, **kwargs):
  cp = ConfigParser.ConfigParser()
  cp.readfp(fo)

  repos = RepoContainer()
  repos.update(original or {})

  for id in cp.sections():
    if id == 'main': continue # skip the [main] section
    kwargs['id'] = id
    for option in cp.options(id):
      kwargs[option] = cp.get(id, option).strip()
    repos.add_repo(cls(**kwargs), 
                   ignore_duplicates=ignore_duplicates)
  return repos

from defaults import * # imported last to avoid circular ref

class RepoFileParseError(Exception):
  def __str__(self):
    return 'Error parsing repo file \'%s\'; error was:\n%s' \
           % (self.args[1], self.args[0])

class RepoStringParseError(Exception):
  def __str__(self):
    return 'Error parsing repo string; error was:\n%s' % self.args[0]

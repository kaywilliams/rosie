from dimsbuild.event import Event

API_VERSION = 5.0

class MDSetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'md-setup',
      comes_before = ['MAIN'],
    )
  
  def _run(self):
    for event in self._getroot():
      mddir_dst = self.METADATA_DIR/event.id
      event_mdfile = self.CACHE_DIR/self.cvars['base-vars']['pva']/'builddata'/event.id/'%s.md' % event.id
      if event_mdfile.exists():
        mddir_dst.mkdirs()
        event_mdfile.cp(mddir_dst, link=True, force=True, preserve=True)


class ComposeEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'compose',
      provides = ['composed-tree'],
      comes_after = ['MAIN'],
    )
    
    self.composed_tree = self.TEMP_DIR/'output'
  
  def _run(self):
    self.log(0, "composing output tree")
    self.log(1, "linking output folders")
    self.composed_tree.mkdirs()
    
    for event in self._getroot():
      event_output_dir = self.METADATA_DIR/event.id/'output'
      if event_output_dir.exists():
        event_output_dir.listdir(all=True).cp(self.composed_tree,
                                              recursive=True,
                                              link=True,
                                              force=True,
                                              preserve=True)
  
  def _apply(self):
    self.cvars['composed-tree'] = self.composed_tree


class CacheOutputEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'cache-output',
      requires = ['composed-tree'],
    )
  
  def _run(self):
    self.log(0, "caching output")
    cache_dir = self.CACHE_DIR/self.cvars['base-vars']['pva']
    cache_dir.rm(recursive=True, force=True)
    cache_dir.mkdirs()
    
    self.log(1, "caching output tree")
    self.cvars['composed-tree'].rename(cache_dir/'output')
    
    self.log(1, "caching metadata")
    self.METADATA_DIR.rename(cache_dir/'builddata')
    
    self.DISTRO_DIR.removedirs()


EVENTS = {'ALL': [MDSetupEvent, ComposeEvent, CacheOutputEvent]}

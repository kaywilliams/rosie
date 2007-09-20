from dimsbuild.event import Event

API_VERSION = 5.0

class ComposeEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'compose',
      provides = ['composed-tree'],
      comes_after = ['MAIN'],
    )
    
    self.composed_tree = self.DISTRO_DIR/'output'
  
  def run(self):
    self.log(0, "composing output tree")
    self.log(1, "removing old output tree")
    self.composed_tree.rm(recursive=True, force=True)
    
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
  

  def apply(self):
    self.cvars['composed-tree'] = self.composed_tree

EVENTS = {'ALL': [ComposeEvent]}

from dimsbuild.event import Event

from dimsbuild.modules.installer.lib import FileDownloadMixin

API_VERSION = 5.0

class Stage2ImagesEvent(Event, FileDownloadMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'stage2-images',
      provides = ['stage2'],
      requires = ['anaconda-version', 'source-vars'],
    )
    
    self.DATA = {
      'input':  [],
      'output': [],      
    }
    
    self.mdfile = self.get_mdfile()
    
    FileDownloadMixin.__init__(self, self.getBaseRepoId())
  
  def _setup(self):
    self.setup_diff(self.mdfile, self.DATA)
    self.register_file_locals(L_FILES)
  
  def _clean(self):
    self.remove_output(all=True)
    self.clean_metadata()
  
  def _check(self):
    return self.test_diffs()
  
  def _run(self):
    self.log(0, "synchronizing stage2 images")
    self.remove_output()
    self.download()
    self.write_metadata()
  
  def _apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to file '%s' at '%s'" % (file.basename, file.dirname))


EVENTS = {'INSTALLER': [Stage2ImagesEvent]}

#------ LOCALS ------#
L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
      <file id="stage2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="netstg2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="hdstg2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
    </files>

    <!-- 10.89.1.1 - netstg2.img and hdstg2.img combined into minstg2.img -->
    <files version="10.89.1.1">
      <action type="delete" path="file[@id='netstg2.img']"/>
      <action type="delete" path="file[@id='hdstg2.img']"/>
      <action type="insert" path=".">
        <file id="minstg2.img">
          <path>
            <string-format string="%s/base">
              <format>
                <item>product</item>
              </format>
            </string-format>
          </path>
        </file>
      </action>
    </files>

    <!-- 11.1.0.51-1 - images moved from $PROD/base/ to images/ -->
    <files version="11.1.0.51-1">
      <action type="update" path="file[@id='stage2.img']">
        <path>images</path>
      </action>
      <action type="update" path="file[@id='minstg2.img']">
        <path>images</path>
      </action>
    </files>

  </files-entries>
</locals>
'''

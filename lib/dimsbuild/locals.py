""" 
locals.py

Local data/settings for dimsbuild
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>"
__version__ = "3.0"
__date__    = "March 13th, 2007"

#---------- LOCALS DATA -----------#

L_IMAGES = ''' 
<locals>  
  <images-entries>
    <images version="0">
      <image id="initrd.img">
        <format>ext2</format>
        <zipped>True</zipped>
        <buildstamp>.buildstamp</buildstamp>
      </image>
      <image id="product.img">
        <format>ext2</format>
        <buildstamp>.buildstamp</buildstamp>
      </image>
      <image id="updates.img">
        <format>ext2</format>
        <buildstamp>.buildstamp</buildstamp>
      </image>
    </images>
    
    <!-- approx 10.2.0.3-1 - initrd.img format changed to gzipped cpio -->
    <images version="10.2.0.3-1">
      <action type="update" path="image[@id='initrd.img']">
        <format>cpio</format>
      </action>
    </images>
    
    <!-- 11.2.0.11-1 - updates.img format changed to gzipped cpio -->
    <images version="11.2.0.11-1">
      <action type="update" path="image[@id='updates.img']">
        <format>cpio</format>
        <zipped>True</zipped>
      </action>
    </images>
  </images-entries>
</locals>
'''

L_BUILDSTAMP_FORMAT = ''' 
<locals>
  <!-- .buildstamp format entries -->
  <buildstamp-format-entries>
    <buildstamp-format version="0">
      <line id="timestamp" position="0">
        <string-format string="%s">
          <format>
            <item>timestamp</item>
          </format>
        </string-format>
      </line>
      <line id="fullname" position="1">
        <string-format string="%s">
          <format>
            <item>fullname</item>
          </format>
        </string-format>
      </line>
      <line id="version" position="2">
        <string-format string="%s">
          <format>
            <item>version</item>
          </format>
        </string-format>
      </line>
      <line id="product" position="3">
        <string-format string="%s">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
    </buildstamp-format>
    <!-- 10.2.0.63-1 - added '.arch' to timestamp -->
    <buildstamp-format version="10.2.0.63-1">
      <action type="update" path="line[@id='timestamp']">
        <string-format string="%s.%s">
          <format>
            <item>timestamp</item>
            <item>basearch</item>
          </format>
        </string-format>
      </action>
    </buildstamp-format>
    <!-- 10.2.1.5 - uncertain of actual revision number - at some point between
         10.1.0.1 and 10.2.1.5 'webloc' was added -->
    <buildstamp-format version="10.2.1.5">
      <action type="insert" path=".">
        <line id="webloc" position="4">
          <string-format string="%s">
            <format>
              <item>webloc</item>
            </format>
          </string-format>
        </line>
      </action>
    </buildstamp-format>
  </buildstamp-format-entries>
</locals>
'''

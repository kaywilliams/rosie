from spin.locals import *

class LocalsMixin:
  def __init__(self):
    self.locals = LocalsObject(self)

class LocalsObject:
  "Dummy container object for locals information"
  def __init__(self, ptr):
    self.ptr = ptr

  ver = property(lambda self: self.ptr.cvars['anaconda-version'])

  files            = property(lambda self: FILES_LOCALS[self.ver])
  buildstamp_fmt   = property(lambda self: BUILDSTAMP_FORMAT_LOCALS[self.ver])
  discinfo_fmt     = property(lambda self: DISCINFO_FORMAT_LOCALS[self.ver])
  logos            = property(lambda self: LOGOS_LOCALS[self.ver])
  installclass     = property(lambda self: INSTALLCLASS_LOCALS[self.ver])
  release_html     = property(lambda self: RELEASE_HTML[self.ver])
  gdm_custom_theme = property(lambda self: GDM_CUSTOM_THEME[self.ver])
  logos_files      = property(lambda self: LOGOS_RPM_FILES_LOCALS[self.ver])
  theme_files      = property(lambda self: THEME_RPM_FILES_LOCALS[self.ver])

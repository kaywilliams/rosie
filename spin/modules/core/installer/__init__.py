from spin.event import Event, CLASS_META

API_VERSION = 5.0
EVENTS = {'os': ['InstallerEvent']}

class InstallerEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'installer',
      properties = CLASS_META,
      provides = ['os-content'],
      suppress_run_message = True,
    )

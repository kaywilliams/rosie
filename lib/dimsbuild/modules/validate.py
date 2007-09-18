from dimsbuild.event import Event, EventExit

API_VERSION = 5.0

class ValidateEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'validate',
      comes_after = ['init'],
      conditionally_comes_after = ['clean'],
    )
  
  def _add_cli(self, parser):
    parser.add_option('--validate',
                      default=None,
                      dest='validate',
                      metavar='[distro|dimsbuild]',
                      help="validates the distro.conf or dimsbuild.conf and exits",
                      choices=['distro', 'dimsbuild'])
  
  def _apply_options(self, options):
    if options.validate is not None:
      self.cvars['exit-after-validate'] = True
      self.cvars['validate'] = options.validate
  
  def run(self):
    self.log(0, "performing config validation")
    if self.cvars.get('validate', 'distro') == 'distro':
      self.log(1, "validating distro.conf")
      self._validate('/distro/main', schemafile='main.rng', what='distro')
    else:
      self.log(1, "validating dimsbuild.conf")
      self._validate('/dimsbuild', schemafile='dimsbuild.rng', what='dimsbuild')
  
    if self.cvars.get('exit-after-validate', False):
      self.log(4, "exiting because the '--validate' option was used at command line")
      raise HookExit


EVENTS = {'ALL': [ValidateEvent]}

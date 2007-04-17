""" 
modules

A 'module' is  a unit of code that  performs some task in the process  of building
a  DiMS distribution.   Modules  are executed sequentially in  an order defined by
the dispatcher; see dispatch.py for more details on how this ordering is computed.
They  exist as  a part  of a  modular  build  system in which each  module can  be
individually  enabled,  disabled, or executed as part of the standard operation of
the program.   Additional modules can be defined  at any  time and easily inserted
into the build process at any point.   This  file attempts to describe the process
of making a custom dimsbuild module.

A dimsbuild module is a python module with the following properties:
 * contains an EVENTS dictionary defining one or more events
 * defines zero or more EventInterfaces, usually through subclassing
 * defines zero or more hook functions
See below for a description of each of these items.   The only required feature is
the EVENTS  dictionary with at least one  event-type struct;  the rest is optional
(though usually present).
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftare.com>"
__version__ = "3.0"
__date__    = "March 13th, 2007"

# from interface import EventInterface
# from dispatch import EVENT_TYPE_PROC, EVENT_TYPE_MARK

""" 
The EVENTS dictionary  contains a list of the events that this module defines. The
event name serves as the eventid for  the EventManager class that  manages program
events  and must be unique  across all modules.  The interface element is a string
that says  which interface the  EventManager should  instantiate and pass  to hook
functions when this event is raised.  The event type is the kind of event this is;
the  default is EVENT_TYPE_MARK.  Provides  and requires are lists of strings that
define provisions and requirements of this event; these are used by the dispatcher
to resolve the order of event execution.  A module must define at least one event.

The EventInterface supplied  as the argument  to 'interface' can  be any  subclass
of  the EventInterface superclass  defined  in  interface.py.  It is specified  as
a string as opposed to an actual instance so that the instance can be instantiated
at a  later time as  needed.  The interface  need not be defined  directly in this
module; however, it  must be defined in  one of the  enabled modules  in order for
dimsbuild to execute the event properly.

The  type of the event determines how the EventManager generates  execution events
for this event.  EVENT_TYPE_MARK is a 'marker event', meaning it merely represents
a moment in time in the execution of a program.  For example, the 'applyopt' event
signifies  the  moment  at which  the  main  program has  completed modifying  its
OptionParser;  other modules can  hook onto this  event in order  to add their own
options.  EVENT_TYPE_PROC  represents 'process events', or events that relate to a
some amount of processing that will occur.  The EventManager  handles these events
a little differently; instead  of generating a single event for process events, it
generates  three:  one  before the event  itself  is raised, one  representing the
actual event, and one after it  finishes.  This allows modules to modify the input
and/or  output of  the process  without having to  actually override  the function
itself.  Process  events  raised  by  the  EventManager are  called  'pre<event>',
'<event>', and 'post<event>', respectively.

In order to get an event to occur at a specific place in the process of dimsbuild,
the 'provides' and 'requires' fields must  be set appropriately.  If, for example,
a new event  needs to run after the 'comps' event  defined in  comps.py, it should
include 'comps.xml' in its 'requires' list  ('comps.xml' is one  of the provisions
in the  'provides' list of comps.py).  If  this event  must  occur  before another
event, then it should define  a provision in  the 'provides' list; then, the other
event's  'requires' list  should  be  modified  to  include  this  new event.  For
example, to get a new event to run before the 'comps' event, add 'newevent' to the
'provides' list in newevent.py and to the 'requires' list in comps.py.

See  event.py for more details  on the content of  the various fields of the EVENT
struct.
"""

#EVENTS = {
#  '<eventname>': {
#    'interface': '<InterfaceName>'
#    'type': EVENT_TYPE_PROC|EVENT_TYPE_MARK
#    'provides': [<list of provisions>]
#    'requires': [<list of requirements>]
#  },
#}

""" 
Interfaces are  special classes that are passed  to hook functions when they are
called  by the dispatcher.   They provide the hook function with access to class
variables and functions of the main program.  See event.py for more information.
A module may define zero or more Interfaces.
"""

# class ExampleInterface(EventInterface): pass

""" 
Hook  functions are functions that  'hook'  on to an event in  program execution;
that is,  they are called when  the program reaches a  certain point in execution
and 'raises' that event.   They are passed an Interface  as their first  argument
which  provides them a  way to communicate to the main program itself.   They may
accept  additional parameters;  however, in the case of most  dimsbuild  modules,
additional parameters are not passed - thus, all parameters must be available via
the interface.   Hook functions are named  <eventname>_hook, where <eventname> is
the  name of the event they wish to hook.   A module may define zero or more hook
functions.   Additionally,  a module can hook events  defined in other modules if
desired.
"""

# def <eventname>_hook(interface, *args, **kwargs): pass

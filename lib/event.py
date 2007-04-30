""" 
event.py

Event management for dimsbuild

Defines an Event class which represents a single unit of program execution.  Events
are managed by a Dispatch class, which is responsible for registering, organizing,
and executing Events in a given order.

A Dispatch object is responsible for controlling the overall program flow of
whatever program it is associated with.  It iterates over a series of steps, or
'events', which can be 'hooked' by functions defined in external program modules in
order to perform some program-related task.  Events can be individually enabled and
disabled in multiple ways, including through user input, reading program
configuration, and by program modules at runtime.  Additional control is given by
providing functions that allow iterating through events forwards and backwards.
Typically, a program finishes execution once the final Event is raised and all
functions that hook it have returned.

Events are typically defined in a program module inside an EVENTS list.  The EVENTS
list constains zero or more events that are registered with a dispatch instance and
raised during the dispatch process.  The content of an event struct is described
below in the EventFromStruct() factory function.

In order to compute the order of event processing, 'provides' and 'requires' fields
are used in an attempt to resolve a dependency ordering.  These fields are similar
in function to the 'Provides:' and 'Requires:' fields of an RPM spec file in that
all of the requirements of a specific event must be satisified before it can be run.
See resolver.py for more information as to how actual event resolution order is
computed.

Note: this could probably be removed from dimsbuild and included as a standard
DiMS library.
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>"
__version__ = "2.0"
__date__    = "April 17th, 2007"

import dims.tree as tree

import resolve

from interface import EventInterface

#------ EVENT TYPES ------#
""" 
Event properties - the following are supported properties on Events.

bit 0 : PROP_HAS_PRE
        Property denoting whether an event has a 'preevent'.  Preevents run before
        the execution of the main event, and are exposed via the hooking system to
        allow other modules/plugins to hook and modify the input to the event
bit 1 : PROP_HAS_POST
        Property denoting whether an event has a 'postevent'.  Postevents are
        identical to prevents except that they run after the execution of the main
        event and are exposed to that event output can be modified.
bit 2 : PROP_CAN_DISABLE
        Property indicating whether an event can be controlled by the user via
        command-line arguments.
bit 3 : PROP_META
        Property indicating whether an event can be considered a special 'meta
        event', which is a grouping of other events.  Meta events have special
        behavior when enabled and disabled in that changes to their enabled status
        propagate to their immediate children.

Properties can be combined using bitwise operations (& and |) to enable and
disable certain properties as required by the specific Event.
"""
PROP_HAS_PRE     =    1
PROP_HAS_POST    =   10
PROP_CAN_DISABLE =  100
PROP_META        = 1000

""" 
Event types - a few convenience bitmasks to use as the basis for events.  These event
types can be combined using standard bitwise arithmetic, as normal.

EVENT_TYPE_MARK ('marker events')
  Marker events are events that signify a certain point in the execution of
  a program.  They do not have either a pre or post event, and without the added
  capability, they can't be enabled or disabled.
EVENT_TYPE_PROC ('process events')
  Process events are events that are associated with a specific process in program
  execution; for example, with the execution of a certain function.  They have pre
  and post events that are called immediately before and after the execution of this
  process.  These events are also disableable, which will prevent the process from
  running, but not the pre and post events.
EVENT_TYPE_CTRL ('control events')
  Control events are generally reserved for the main program to define and use; they
  are treated as special in that they cannot be disabled by the user.
EVENT_TYE_MDLR ('modular events')
  Modular events are typically defined by program modules.  As such, they can be
  enabled and disabled normally by the user.
EVENT_TYPE_META ('meta events')
  Meta events are special events that have different behavior from other events.  A
  meta event is usually a container for other events and doesn't have hook functions
  of its own.  It does have pre and post events, both of which can be hooked normally.
"""

EVENT_TYPE_MARK = 0000
EVENT_TYPE_PROC = 0011
EVENT_TYPE_CTRL = 0000
EVENT_TYPE_MDLR = 0100
EVENT_TYPE_META = 1111


#------ CLASSES ------#
class Event(resolve.Item, tree.Node):
  """ 
  An object representing an event in program execution
  
  An Event must have an Interface and one or more functions registered before
  it can be executed.  An Interface is essentially a class used as a method of
  communication between the main program and a hook function.  Each function
  registered with an Event instance is called with an instance of the registered
  Interface as its first argument.  See interface.py for more details on the
  creation and usage of the Interface class.
  
  Subclasses the Item class of resolve.py as well as the Node class of tree.py.
  As such, it inherits the ability to be used in a dependency-solution algorithm
  ('provides' and 'requires' lists) as well as the necessary pointers to be
  arranged in a tree-like structure.
  """
  def __init__(self, name, provides=[], requires=[],
                     properties=EVENT_TYPE_MARK|EVENT_TYPE_CTRL,
                     interface=None):
    """ 
    Event instances have the following fields in addition to those inherited
    from its parents:
     * properties : bitmask of event properties - see event type descriptions
                    for an explanation of the values
     * inteface   : pointer to the interface that will be instantiated by
                    this Event and passed to each of its registered
                    functions when it is executed
     * functions  : list of registered functions; these functions are called
                    sequentially with an instance of the interface defined
                    in self.interface whenever this Event is executed
     * pre        : pointer to the Event's 'preevent', which precedes this
                    event's own execution.  This is None for events that do
                    not have the EVENT_TYPE_PROC property.
     * post       : pointer to the Event's 'postevent', which follows this
                    event's own execution.  This is None for events that do
                    not have the EVENT_TYPE_PROC property.
    """
    resolve.Item.__init__(self, provides, requires)
    tree.Node.__init__(self, name)
    
    self.properties = properties
    self.interface = interface
    
    self.functions = []
    
    if self.test(PROP_HAS_PRE):
      self.pre = Event('pre%s' % self.id, interface=self.interface)
    else:
      self.pre = None
    if self.test(PROP_HAS_POST):
      self.post = Event('post%s' % self.id, interface=self.interface)
    else:
      self.post = None
  
  def __iter__(self): return EventIterator(self)
  def __str__(self): return self.id
  def __repr__(self): return '<events.Event instance id=\'%s\'>' % self.id
  
  #------ BITMASK FUNCTIONS ------#
  def test(self, property): return self.properties & property
  
  #------ ENABLING/DISABLING FUNCTIONS ------#
  def enable(self):  self._set_enable_status(True)
  def disable(self): self._set_enable_status(False)
  def _set_enable_status(self, status):
    self.enabled = status
    if self.test(PROP_META):
      for event in self.get_children():
        event._set_enable_status(status)
  
  #------ REGISTRATION FUNCTIONS ------#
  def register_function(self, function, sub=None):
    """ 
    Register a function to be run when this Event is executed.  The function must
    accept an Interface as its first argument.
    """
    if sub is None:
      self.functions.append(function)
    elif sub == 'pre':
      self.pre.functions.append(function)
    elif sub == 'post':
      self.post.functions.append(function)
    else:
      raise ValueError, 'Invalid value for sub: \'%s\'' % sub
  
  def register_interface(self, interface, force=False):
    """ 
    Register an Interface to be passed to all registered functions when this Event
    is executed.
    """
    if self.interface is None or force:
      self.interface = interface
      if self.test(PROP_HAS_PRE):
        self.pre.register_interface(interface, force)
      if self.test(PROP_HAS_POST):
        self.post.register_interface(interface, force)
    else:
      raise RegisterInterfaceError, 'interface %s already registered' % self.interface
  
  #------ ITERATION FUNCTIONS ------#
  def next(self):
    return self.firstchild or self.nextsibling or None
  
  def prev(self):
    return self.prevsibling or self.parent or None
  
  #------ EXECUTE ------#
  def run(self, force=False, *args, **kwargs):
    """ 
    Create an instance of the registered interface and pass it as an argument
    to all registered functions.  If this Event has the EVENT_TYPE_PROC property,
    also do so to the event's pre and post events.
    """
    interface = self.interface(*args, **kwargs)
    try:
      if self.test(PROP_HAS_PRE):
        for hfunc in self.pre.functions:  hfunc(interface)
      if self.enabled or force:
        for hfunc in self.functions:      hfunc(interface)
      if self.test(PROP_HAS_POST):
        for hfunc in self.post.functions: hfunc(interface)
    except HookExit, e:
      print e
      sys.exit()
    
  #------ TREE FUNCTION WRAPPERS ------#
  # children/sibling wrappers, make sure provides lists are updated
  def append_child(self, child):
    tree.Node.append_child(self, child)
    self.__add_provs(child.provides)
  def prepend_child(self, child):
    tree.Node.prepend_child(self, child)
    self.__add_provs(child.provides)
  
  def append_sibling(self, sibling):
    tree.Node.append_sibling(self, sibling)
    if self.parent is not None:
      self.parent.__add_provs(sibling.provides)
  def prepend_sibling(self, sibling):
    tree.Node.prepend_sibling(self, sibling)
    if self.parent is not None:
      self.parent.__add_provs(sibling.provides)
  
  def __add_provs(self, provisions):
    for prov in provisions:
      if prov not in self.provides: self.provides.append(prov)


class Dispatch:
  """ 
  The primary dispatch class; handles Event, Interface, and hook function
  processing and registration.
  
  After instantiating a Dispatch object, events and functions can be registered
  using the appropriate register_*() functions.  The ordering of registration
  does not matter; that is, a function that hooks onto a 'start' event can be
  registered before the 'start' event itself is actually registered.  No checking
  is performed until the commit() function is called.  This function attempts to
  create an event tree and register all functions based on the contents of its
  unregistered_* sequences, and will raise an exception if unable to do so.
  """
  def __init__(self):
    """ 
    Initializes Dispatch variables.  Dispatch instances have the following
    fields:
     * event     : an Event instance with id 'ALL'; forms the root of the
                   Event tree associated with this Dispatch instance (all
                   events should be a child or subchild of this Event)
     * currevent : the current event of the dispatcher.  The contents of
                   this value are adjusted as events are processed
     * iter      : an iterator over self.event.  This value is None until
                   self.commit() is run
     * force     : list of events that will be forced to execute when running
                   process().  The purpose of this list is to allow the
                   status of events to be ultimately controlled beyond what
                   the ordinary execution of code would indicate; for
                   example, by a user's command-line arguments
     * skip      : list of events that will be skipped when running process().
                   Like self.force, this is intended to provide a greater
                   degree of control over the execution of events at runtime.
                   self.skip has a higher priority than self.force
     * committed : boolean indicating whether commit() has been executed
     * unregistered_events : list of events that have not yet been actually
                   registered with the dispatcher.  Event registration is a 
                   two step process - because events can be registered in any
                   order, an event may request a parent that does not exist yet.
                   Thus, events aren't completely registered until commit() is
                   called.
     * unregistered_functions : dictionary of functions that have not yet been
                   registered.  As with self.unregistered_events, above,
                   functions can be defined in program modules that hook onto
                   events that have not yet been registered with the dispatcher.
                   These functions are similarly registered when commit() is
                   called.
    """
    self.event = Event('ALL', properties=EVENT_TYPE_META)
    self.event.register_interface(EventInterface) # hack
    self.currevent = None
    self.iter = None
    
    self.force = []
    self.skip = []
    self.committed = False
    self.unregistered_events = []
    self.unregistered_functions = {}
  
  def __iter__(self):
    self._test_commit()
    return iter(self.event)

  def _test_commit(self):
    "Raises a DispatchError if self.committed is False"
    if not self.committed:
      raise DispatchError, "Dispatch is not committed"
  
  #------ EXECUTION FUNCTIONS ------#
  def process(self, *args, **kwargs):
    """ 
    Iterate over the events contained in this Dispatch object, raising them one
    at a time until the final event is executed.  process() can't be run until
    commit() has successfully completed.
    """
    self._test_commit()
    while True:
      try:
        self.next()
        self.raise_event(*args, **kwargs)
      except StopIteration: break
  
  def raise_event(self, *args, **kwargs):
    """ 
    Raise the Event self.currevent, causing all functions that hook it to execute.
    """
    if self.currevent is None: return
    if self.currevent.id in self.skip: return
    if not self.currevent.enabled and self.currevent.id not in self.force: return
    self.currevent.run((self.currevent.id in self.force), *args, **kwargs)
  
  #------ COMMIT FUNCTIONS ------#
  def commit(self):
    """ 
    Commit event and function registrations
    
    Due to the fact that events and functions can be registered in any order, the
    dispatcher cannot ascertain that a given Event's requested parent exists, or
    that the Event a function is trying to hook actually exists.  Instead, once
    all event and functions have been registered individually, commit() is called
    in order to finish off the process.  Specifically, commit() is responsible for
    constructing an event tree and resolving event execution order as well as with
    registering hook functions with the appropriate events.
    """
    self.__process_unregistered_events()
    self.__process_unregistered_functions()
    self.__resolve()
    self.committed = True
    self.iter = iter(self)
  def uncommit(self):
    "'Uncommit' this dispatch object"
    self.comitted = False
    self.iter = None

  def __process_unregistered_events(self):
    """ 
    Attempt to build an event tree from self.unregistered_events.  Basic algorithm
    is to loop over the unregistered event list and attempt to register each one.
    Those that fail are placed at the end of the list.  In each iteration, so long
    as at least one event was successfully placed into the event tree, the process
    can continue.  If, however, an entire loop completes without a single event
    registration, then the Event set is unresolvable and a DispatchError is raised.
    """
    # register all events
    firstunreg = None
    while True:
      try:
        event, parentid = self.unregistered_events.pop(0)
      except IndexError:
        break # we're done
      try:
        self.register_event_by_id(event, parentid=parentid)
        firstunreg = None
      except UnregisteredEventError:
        if event == firstunreg: # we've gone a complete loop without registering anythimg
          raise DispatchError, "Unable to completely register all events"
        self.unregistered_events.append((event, parentid))
        if firstunreg is None: firstunreg = event
    
  def __process_unregistered_functions(self):
    """ 
    Attempt to register all functions with their respective events.  If the Event
    in question doesn't exist, raise an UnregisteredEventError.
    """
    # register all functions
    for eventid, funcs in self.unregistered_functions.items():
      event = self.get(eventid) # handles pre and post replacement, if necessary
      if event is None: raise UnregisteredEventError, eventid
      for f in funcs:
        if eventid.startswith('pre'):
          event.register_function(f, sub='pre')
        elif eventid.startswith('post'):
          event.register_function(f, sub='post')
        else:
          event.register_function(f, sub=None)
    self.unregistered_functions = {}
  
  def __resolve(self, event=None):
    "Recursively perform dependency resolution at each level of the event tree."
    if event is None: event = self.event
    for child in event.get_children():
      self.__resolve(child)
    tree.stitch(resolve.resolve(event.get_children()), event)
  
  #------ ITERATION FUNCTIONS ------#
  def next(self): self.move(1)
  def prev(self): self.move(-1)
  def move(self, step=1):
    self._test_commit()
    self.currevent = self.iter.advance(step)
  
  def get(self, eventid, err=False):
    """ 
    Event = self.get(eventid[, err])
    
    Search the event tree for an event with id eventid.  If found, return the
    event.  If not found and err is False, return None; else raise an
    UnregisteredEventError.  Getting a pre or post event will return the base
    event (for example, self.get('pregen') will get the 'gen' event, if it
    exists).
    """
    type = None
    if eventid.startswith('pre'):
      eventid = eventid.replace('pre', ''); type = 'pre'
    elif eventid.startswith('post'):
      eventid = eventid.replace('post', ''); type = 'post'
    for e in self.event:
      if e.id == eventid:
        if type is None:            return e
        elif type == 'pre':
          if e.test(PROP_HAS_PRE):  return e
        elif type == 'post':
          if e.test(PROP_HAS_POST): return e
    if err:
      raise UnregisteredEventError, eventid
    else:
      return None
  
  #------ EVENT REGISTRATION FUNCTIONS ------#
  def register_event(self, event, parent=None, prepend=False):
    "'Register' an Event with this Dispatch instance"
    if self.get(event.id) is not None:
      raise RegisterEventError, "event id '%s' already registered" % event.id
    else:
      if prepend: (parent or self.event).prepend_child(event)
      else:       (parent or self.event).append_child(event)
  def register_event_by_id(self, event, parentid=None, prepend=False):
    "Register an event, setting its parent to parentid"
    parent = self.get(parentid or 'ALL')
    if parent is None: raise UnregisteredEventError, parentid
    self.register_event(event, parent=parent, prepend=prepend)
  
  def register_function(self, function, eventid):
    "Register a function to the event identified by eventid"
    if not self.unregistered_functions.has_key(eventid):
      self.unregistered_functions[eventid] = []
    self.unregistered_functions[eventid].append(function)
  
  #------ MODULE LOADING FUNCTIONS ------#
  def process_module(self, module):
    """ 
    Process an already-loaded python module, attempting to load any Event,
    Interface, and hook function definitions contained within.  The module must
    meet a few requirements in order for this function to work:
    
     * must have an EVENTS list defined with zero or more event structs (see
       EventFromStruct() factory function)
     * for every event struct, must have a definition for the interface specified
       in the 'interfaces' attribute.  This can be a class definition in the file
       itself or the module can import an interface definition from another file
     * if the module wishes to register any hook functions, these functions must
       be named according to the following scheme: <eventid>_hook, where <eventid>
       is the id of the Event the function wishes to hook.  For example, if the
       EVENTS list defines an event named 'initrd', then a hook function onto this
       event would be named 'initrd_hook'.  Note: the module isn't limited to
       hooking events defined in the same file; it can hook events from any other
       program module as well.
    
    Raises a DispatchError if the dispatcher is already committed.  Raises
    ImportErrors at several stages of the process if the import fails for any
    reason.
    """
    if self.committed:
      raise DispatchError, "Cannot register module %s, already committed" % module
    
    # get events and associated interfaces...
    if hasattr(module, 'EVENTS'):
      for struct in module.EVENTS:
        event = EventFromStruct(struct)
        self.unregistered_events.append((event, struct.get('parent', 'MAIN')))
        if struct.has_key('interface'):
          if hasattr(module, struct['interface']):
            interface = getattr(module, struct['interface'])
          else:
            raise ImportError, "Missing definition for interface '%s' in module %s" % (struct['interface'], module)
        else:
          interface = EventInterface
        event.register_interface(interface)
    else:
      raise ImportError, "Missing definition for EVENTS variable in module %s" % module
    
    # ... and get functions
    for attr in dir(module):
      if attr.endswith('_hook'):
        eventid = attr.replace('_hook', '')
        self.register_function(getattr(module, attr), eventid)

  
class EventIterator:
  "Basic iterator over Event-type objects"
  def __init__(self, eventtree):
    self.order = []
    for event in tree.depthfirst(eventtree):
      self.order.append(event)
    self.reset() # sets self.index to -1
    self.reversed = False
  
  def next(self):
    self.index += 1
    if self.index >= len(self.order):
      raise StopIteration
    else:
      return self.order[self.index]
  
  def prev(self):
    self.index -= 1
    if self.index < 0:
      raise StopIteration
    else:
      return self.order[self.index]
  
  def reset(self):
    self.index = -1
  
  def reverse(self):
    self.order.reverse()
    self.reversed = not self.reversed
    self.reset()
  
  def advance(self, amount=1):
    newindex = self.index + amount
    if newindex < 0 or newindex >= len(self.order):
      raise StopIteration
    else:
      self.index = newindex
    return self.order[self.index]


#------ FACTORY FUNCTIONS ------#
def EventFromStruct(struct):
  """ 
  Event = EventFromStruct(struct)
  
  Process a dictionary struct and create an Event instance from it.
  
  An event struct can contain the following keys:
   * id (required): a unique id for this Event
   * interface (required): a pointer to an Interface object that will be passed
     to all function hooking this Event
   * properties (optional): any properties the event can have - see description
     of properties for more details
   * provides (optional): a list of strings describing what the execution of
     this event provides to other events.  For example, an event that creates a
     file called 'globalstrings' might put 'globalstrings' as one of its provides
     strings.  This is one of two fields used by the resolver to determine the
     order of event execution
   * requires (optional): a list of strings describing what must be provided by
     one or more prior events in order for this one to execute.  For example, an
     event that requries a file called 'globalstrings' might put 'globastrings'
     in its requires string list.  This is the second of two fields used by the
     resolver to determine the order of event execution
   * parent (optional): the id of this Event's parent
  """
  id = struct.get('id')
  properties = struct.get('properties', EVENT_TYPE_MARK|EVENT_TYPE_CTRL)
  provides = struct.get('provides', [])
  requires = struct.get('requires', [])
  return Event(id, provides=provides, requires=requires, properties=properties)


#------ EXCEPTIONS ------#
class DispatchError(StandardError):
  "General class of dispatch exceptions"
class UnregisteredEventError(StandardError):
  "Class of exceptions raised when attempting to manipulate a nonexistent event"
  def __str__(self): return 'The \'%s\' event is not registered' % self.args[0]
class RegisterEventError(StandardError):
  "Class of exceptions raised when an event can't be registered for any reason"
  def __str__(self): return 'Cannot register event: %s' % self.args[0]
class RegisterInterfaceError(StandardError):
  "Class of exceptions raised when an interface can't be registered for any reason"
  def __str__(self): return 'Cannot register interface: %s' % self.args[0]

class HookExit(Exception):
  "Class of exceptions raised when a module/plugin wishes to halt program execution"

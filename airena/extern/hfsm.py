# -*- coding: utf-8 -*-

"""
This module provides a simple but powerful way to define testable, hierarchical finite state machines. You should
know how a state machine works. This implementation provides following features:

* guard action
* entry and exit actions
* transition action
* external and local transitions, see: https://en.wikipedia.org/wiki/UML_state_machine#Local_versus_external_transitions
* hierarchically nested states, see: https://en.wikipedia.org/wiki/UML_state_machine#Hierarchically_nested_states
* testable
* clear defined events interface
* clear defined actions interface
* execution speed optimization (transitions are converted to lookups in a dictionary, even for a hierarchical structure)
* memory efficient because state machine structure can be shared by all instances




References:

#. https://en.wikipedia.org/wiki/State_pattern.
#. https://en.wikipedia.org/wiki/Finite-state_machine.
#. https://en.wikipedia.org/wiki/UML_state_machine.





.. todo:: tutorial (explaining the abilities, entry/exit/actions/guard, different kinds of transitions)
.. todo:: set log level through event handling method?? so one could debug one instance of a statemachine at once.
.. todo:: python debug mode should log what it does but respect the debug level (?)

Versioning scheme based on: http://en.wikipedia.org/wiki/Versioning#Designating_development_stage

::

      +-- api change, probably incompatible with older versions
      |     +-- enhancements but no api change
      |     |
    major.minor[.build[.revision]]
                   |
                   +-|* 0 for alpha (status)
                     |* 1 for beta (status)
                     |* 2 for release candidate
                     |* 3 for (public) release


.. versionchanged:: 2.0.2.0
    introduced __versionnumber__ because __version__ should be a string according to PEP8.
    __versionnumber__ is a tuple containing int as used in the versioning scheme. This 
    way its comparable out of the box, e.g. __versionnumber__ >= (2, 2, 3)


The source repository can be found here: http://dr0id.bitbucket.org/symplehfsm/index.html
"""
__versionnumber__ = (2, 0, 2, 0)
__version__ = ".".join(map(str, __versionnumber__))

__author__ = "dr0iddr0id {at} gmail [dot] com (C) 2010-2012"


import unittest
import logging
import collections


if __file__:
    LOG_FILENAME = __file__ + '.log'
else:
    LOG_FILENAME = __module__ + '.log'

logger = logging.getLogger("symplehfsm")    # pylint: disable=C0103
# loglevel = logging.DEBUG    # pylint: disable=C0103
loglevel = logging.INFO    # pylint: disable=C0103
logger.setLevel(loglevel)
if __debug__:
    _ch = logging.StreamHandler()   # pylint: disable=C0103
    _ch.setLevel(logging.DEBUG)
    logger.addHandler(_ch)
handler = logging.FileHandler(LOG_FILENAME)  # pylint: disable=C0103
handler.setLevel(loglevel)
logger.addHandler(handler)

# -----------------------------------------------------------------------------

class StateUnknownError(Exception):
    """
    Exception raised if the state is not known in the structure.
    """
    pass

# -----------------------------------------------------------------------------


class BaseState(object):
    """
    BaseState from which all hirarchical states should inherit.
    :Note: The state itself is 'stateless'.

    :Parameters:
        name : string
            name of this state
        parent : BaseState
            Reference to the parent state, for the root state use None
            (only one state has None as parent since there is only
            one root)

    """
    class InitialStateAlreadySetError(Exception):
        """Exception is raised if initial state is already set."""
        pass

    class InitialNotSetError(Exception):
        """Exception raised if the initial state is not set."""
        pass

    class InitialNotReplacedError(Exception):
        """Exception raised if the initial state is not replaced."""
        pass

    class ParentAlreadySetError(Exception):
        """Exception raised when a child has already a parent set"""
        pass

    class ReplacementStateIsNotChildError(Exception):
        """Exception raised if the replaced initial state is not a child."""
        pass

    class WrongParentError(Exception):
        """
        Exception raised if the set parent is not the same state
        containint it as child
        """
        pass

    def __init__(self, name=None, parent=None):
        self.initial = None
        self.children = []
        self.optimized = collections.defaultdict(lambda: (None, [], None))
        self.entry = None
        self.exit = None
        self.events = {}  # {event:trans}
        self.parent = None
        if parent:
            parent.add(self)
        self.name = str(id(self))
        if name:
            self.name = name

    def add(self, child, initial=False):
        """
        Adds another state as child to this state.

        :Parameters:
            child : BaseState
                the child state to add
            initial : bool
                defaults to False, if set, the child state is the
                initial state.
        :raises: ParentAlreadySetError if the childs parent is already set.
        :raises: InitialStateAlreadySetError if another initial state has already been defined.
        """
        if child.parent is not None:
            raise self.ParentAlreadySetError(
            "child state '{0}' has already a parent {1} when trying to add it to {2}".format(child, child.parent, self))
        if initial:
            if self.initial is not None:
                raise self.InitialStateAlreadySetError(\
                        str.format("initial already set to {1} for state {0}", self, self.initial))
            self.initial = child
        child.parent = self
        self.children.append(child)
        return child

    def remove(self, child, replace=None):
        """
        Removes a child state. If the removed child state was the initial
        state it has to be replaced.

        :Parameters:
            child : BaseState
                child state to be removed.
            replace : BaseState
                the new initial state if the removed one was the initial state.
                
        :raises: InitialNotReplacedError if the initial state is removed but no other inital state is defined.
        :raises: ReplacementStateIsNotChildError if the initial replacement isn't a child of this state.
        """
        if child in self.children:
            if replace is None:
                if self.initial == child:
                    raise self.InitialNotReplacedError("missing replacement since child {0} \
                                                    to be removed is initial state for {1}".format(self.initial, self))
            else:
                if not self.has_child(replace):
                    raise self.ReplacementStateIsNotChildError("replacement state {0} is not \
                                                    a child of this state {1}".format(replace, self))
                self.initial = replace
            child.parent = None
            self.children.remove(child)

    def has_child(self, child_state):
        """
        Checks if a state has a certain state as a child.

        :Parameters:
            child_state : BaseState
                child_state to check

        :returns:
            bool
        """
        parent = child_state.parent
        while parent:
            if parent is self:
                return True
            parent = parent.parent

        return False

    def is_child(self, parent_state):
        """
        Checks if this state is a child state of a parent state.

        :Parameters:
            parent_state : BaseState
                the parent state to check if this is its child state.

        :returns:
            bool
        """
        parent = self.parent
        while parent:
            if parent is parent_state:
                return True
            parent = parent.parent

        return False

    def check_consistency(self):
        """
        Checks the consistency of the state hierarchy.
        It checks mainly two things:

            - if the initial state is set for each state having a child or
                children, raises InitialNotSetError otherwise
            - if each child of a state has the parent attribute set to that
                state, raises WrongParentError otherwise

        .. deprecated:: 1.0.3.0
            Use :func:`Structure.check_consistency` instead.

        :raises: InitialNotSetError if no initial state has been set when this state has children.
        :raises: WrongParentError if a child has not the parent set where it is a child.
        """
        if self.initial is None and len(self.children) > 0:
            raise self.InitialNotSetError(\
                    "state {0}: initial has to be set if a state has at least one child".format(self))
        for child in self.children:
            if child.parent != self:
                raise self.WrongParentError(\
                "parent {0} of a child {1} is set to another state, should be {2}".format(child.parent, child, self))
            child.check_consistency()

    def __str__(self):
        return str.format("<{0}[{1}]>", self.__class__.__name__, str(self.name))

    __repr__ = __str__

# -----------------------------------------------------------------------------

class Transition(object):
    """
    This class holds the data needed for a transition.

    Represents the transition between (composite) states (just the arrow
    in the state chart).
    The transition itself is 'stateless'.

    :Parameters:
        target_state : State
            The state this transition should change to.
        action : methodcaller
            This should be a methodcaller object or a function
            behaving like a methodcaller. Such a function would
            have following signature (return value is ignored)::

                def f(actions)

            A function behaving like a methodcaller looks like
            this::

                  f = lambda actions: actions.any_method_of_actions()

            :Note: only the function knows which function to call on the actions object.
        guard : methodcaller
            a methodaller of a function that behaves like a methodcaller
            returning a boolean, its signature is::

                guard(actions) -> bool

            If True is returned, then the transition will be followed,
            otherwise the transition will be blocked and event processing
            stops (no parent states are considered).
    """

    def __init__(self, target_state, action=None, guard=None, name=None):
        self.guard = guard
        self.target = target_state
        self.action = action
        self.name = str(id(self))
        if name:
            self.name = name

    def __str__(self):
        return "<{0}[1][guard: {2}, target: {3} action: {4}]>".format(
                                        self.__class__.__name__, str(self.name), self.guard, self.target, self.action)

# -----------------------------------------------------------------------------

class Structure(object):
    """
    This is the class holding the state machine structure, e.g. the number
    of states and their relationship (hierarchy) and its transitions in between them.

    Ths is also the code that is shared by many instances of the same statemachine.

    :Parameters:
        name : string
            Optional name for this instance of this class.
    """

    class RootAlreadySetOrParentMissingError(Exception):
        """
        Exception raised when the parent is missing or the root has already
        been set.
        """
        pass

    class ParentUnkownError(Exception):
        """Exception raised when the parent is unkown."""
        pass

    class EventAlreadyDefinedError(Exception):
        """Exception raised when the event is already defined for that state"""
        pass

    class StateIdentifierAlreadyUsed(Exception):
        """Exception raised when another state has the same state identifier."""
        pass

    def __init__(self, name=None):
        self.states = {}  # {id:State}
        self.root = None
        self.is_optimized = False
        self.name = str(id(self))
        if name:
            self.name = name

    def __str__(self):
        return str.format("<{0}[{1}]>", self.__class__.__name__, str(self.name))

    # #                          name,    parent, initial,            entry,        exit
    # sm_structure.add_state("s0",          None, False,  methodcaller("entry_s0"), context.methodcaller("exit_s0"))
    def add_state(self, state_identifier, parent, initial, entry_action=None, exit_action=None):
        """
        Add a new node representing a state to the structure.

        :Parameters:
            state_identifier : State identifier
                A hashable identifier for that state (name, id, etc.). Has to be unique.
            parent : State identifier
                A hashable identifier of the state that is set as parent.
                The only one state will have set its parent to None, its the root state.
            initial : bool
                Only one of the children of a state can have this set to true, its the
                state that is used to descent to a leaf node of the structure.
            entry_action : methodcaller
                The methodcaller or a function behaving like a methodcaller. That calls
                the entry function on the actions object for that state. Optional, defaults to: None
            exit_action : methodcaller
                The methodcaller or a function behaving like a methodcaller. That calls
                the exit function on the actions object for that state. Optional, defaults to: None
                
        :raises: ParentUnkownError if the parent state identifier is not already known.
        :raises: RootAlreadySetOrParentMissingError if a second root node is added (maybe the parent is missing).
        :raises: StateIdentifierAlreadyUsed if the chosen state identifier is already in use.
        """
        if parent and not parent in self.states:
            raise self.ParentUnkownError("parent of {0} is unkown".format(str(state_identifier)))

        internal_state = BaseState(name=state_identifier)
        internal_state.events = {}  # {event:trans}
        # internal_state.parent = parent
        internal_state.entry = entry_action
        internal_state.exit = exit_action
        if parent:
            self.states[parent].add(internal_state, initial)
        else:
            if self.root:
                raise self.RootAlreadySetOrParentMissingError("root is already set to '{0}' \
                                                or parent of '{1}' is missing".format(self.root, state_identifier))
            self.root = state_identifier
        if state_identifier in self.states:
            raise self.StateIdentifierAlreadyUsed(str(state_identifier))
        self.states[state_identifier] = internal_state

    # #                   handler, event, target,           action,     guard
    # sm_structure.add_trans("s1",   "a",   "s1", methodcaller("action_a"), methodcaller("guard_a"))
    def add_trans(self, state, event, target, action=None, guard=None, name=None):
        """
        Add a transition between two states for a certain event.

        :Parameters:
            state : State identifier
                A hashable identifier for that state (name, id, etc.).
            event : event identifiert
                A hashable event identifier. The same identifiert has to be used
                when calling handle_event on the state machine.
            target : state identifier
                The state this transition will lead too.
            action : methodcaller
                The transition action. Optional, default: None
            guard : methodcaller
                The guard method. Should return a boolean.
                If the return value is True, then the transition is carried out. Otherwise the
                event processing stops and nothing changes.
                
        :raises: StateUnknownError if either the state- or the target-identifier is not known.
        :raises: EventAlreadyDefinedError if this event is already defined for that state.
        """
        if not state in self.states:
            raise StateUnknownError("Unknown state: " + str(state))
        if target is not None and not target in self.states:
            raise StateUnknownError("target not set or unkown")
        internal_state = self.states[state]
        if event in internal_state.events:
            raise self.EventAlreadyDefinedError("state '{0}' has event '{1}' already set".format(\
                                                                                    str(state), str(event)))
        internal_state.events[event] = Transition(target, action, guard, str(name))
        if __debug__:
            logger.debug("added transition to event: {0} : {1}".format(event, str(internal_state.events[event])))

    def do_optimize(self):
        """
        Optimizes the event processing of the state machine. Call this method before you pass
        the structure to the constructor to create a state machine instance.

        .. note::

            It is not recommended to alter the structure after a call to this method, althought now it will
            just update the optimization.

        .. versionchanged:: 2.0.2.0
            Does not raise any exception anymore if called multiple times, it rebuilts internal structure used
            for optimization.

        """
        # collect all possible events
        events = set()
        [events.update(list(x.events.keys())) for x in list(self.states.values())]

        if __debug__:
            logger.info(str(self) + ': all events: ' + str(events))
        # apply alle events to all leaf states to get optimization
        leafs = [x for x in list(self.states.values()) if not x.children]
        if __debug__:
            logger.info(str(self) + ': all states: ' + str(leafs))

        for leaf in leafs:
            leaf.optimized.clear()
            for event in events:
                if __debug__:
                    logger.info("{0}: optimizing state '{1}' for event '{2}".format(self, str(leaf), str(event)))
                guard, methodcalls, target_node = self._get_methodcallers(str(self) + " (optimizing)", event, leaf)
                leaf.optimized[event] = (guard, methodcalls, target_node)
        self.is_optimized = True

    def check_consistency(self):
        """
        Checks the consistency of the state hierarchy.
        It checks mainly two things:

            - if the initial state is set for each state having a child or
                children, raises InitialNotSetError otherwise
            - if each child of a state has the parent attribute set to that
                state, raises WrongParentError otherwise

        .. versionadded:: 2.0.2.0
        """
        self.states[self.root].check_consistency()


    def _get_methodcallers(self, state_machine, event, current_state):
        """
        Computes what 'actions' a transition has to execute for a given state and event.

        :Parameters:
            state_machine : SympleDictHFSM
                The state machine to use, its for log purposes only.
            event : eventidentifier
                The event identifier to know which event to execute.
            current_state : state
                The actual state instance to apply the event (the next state is defined by the
                transitions for that event if defined).

        :Returns:
            tuple containing: (guard, methodcalls, next_state) where
                guard is a methodcaller returning bool
                methodcalls is a list of methodcallers of entry/exit/transition actions in the correct order
                next_state is the the state the state machine has to be after executing that event
                    (note: its not a state identifier, its an instance of BaseState)

        """
        methodcalls = []
        guard = None
        # find the event handling state in the hierarchy
        if __debug__:
            logger.debug(str.format("{0}: handling event '{1}' (current state: '{2}')", \
                                            state_machine, event, current_state))
        source_node = current_state
        nodes = []
        transition = None
        while transition is None:
            if event in source_node.events:
                transition = source_node.events[event]
            if transition is None:
                nodes.append(source_node)
                if source_node.parent:
                    source_node = source_node.parent
                else:
                    break

        if transition is None or transition is False:
            if __debug__:
                logger.debug(\
                    str.format("{0}: no event handling state nor transition found, no state change", state_machine))
            # event not handled
            return guard, methodcalls, current_state
        # transition.guard is here because the exits of the nodes
        # should only be run if the guard returns true

        if __debug__:
            logger.info(str.format("{0}: handling event '{1}' in state '{3}' (current state: '{2}')", \
                                                                    state_machine, event, current_state, source_node))
            if transition and not issubclass(transition.__class__, Transition):
                raise TypeError("transition returned by a state is not a subclass of " + str(Transition))

        if transition.guard:
            guard = transition.guard
        else:
            if __debug__:
                logger.debug(str.format("{0}: transition has no guard function", state_machine))

        if __debug__:
            logger.debug(str.format("{0}: executing transition", state_machine, transition))

        # exits
        for node in nodes:
            if node.exit:
                if __debug__:
                    logger.debug(str.format("{0}: calling exit on state: {1}", state_machine, node))
                methodcalls.append(node.exit)

        # transition
        # go up the hirarchy as needed for the transition, find shared parent state
        if __debug__:
            logger.debug(str.format("{0}: finding parent states of transition...", state_machine))
        target_node = source_node
        if transition.target is not None:
            target_node = self.states[transition.target]
            if __debug__:
                logger.debug(str.format("{0}: source '{1}', target '{2}'", state_machine, source_node, target_node))
            if source_node != target_node:
                if __debug__:
                    logger.debug(str.format("{0}: case source != target", state_machine))
                while not target_node.is_child(source_node):
                    if source_node == target_node:
                        if __debug__:
                            logger.debug(str.format("{0}: found target == source", state_machine))
                        break  # this break is needed
                    else:
                        if source_node.exit:
                            if __debug__:
                                logger.debug(str.format("{0}: calling exit on state: {1}", state_machine, source_node))
                            methodcalls.append(source_node.exit)
                        source_node = source_node.parent
            else:
                if source_node.exit:
                    if __debug__:
                        logger.debug(str.format("{0}: case source == target", state_machine))
                        logger.debug(str.format("{0}: calling exit on state: {1}", state_machine, source_node))
                    methodcalls.append(source_node.exit)
                source_node = source_node.parent

        if transition.action:
            if __debug__:
                logger.debug(str.format("{0}: calling action of transition: {1}", state_machine, transition))
            methodcalls.append(transition.action)
            if __debug__:
                logger.debug("{0}: source '{1}', target '{2}', transition action done".format(\
                                                                        state_machine, source_node, target_node))

        # find child node and go down the hirarchy until target_node is found
        if __debug__:
            logger.debug(str.format("{0}: finding child states for transition...", state_machine))
        if transition.target is not None:
            if source_node != target_node:
                while source_node != target_node:
                    for child in source_node.children:
                        if child == target_node:
                            if target_node.entry:
                                if __debug__:
                                    logger.debug(str.format("{0}: calling entry on: {1}", state_machine, target_node))
                                methodcalls.append(target_node.entry)
                            source_node = target_node
                            break
                        elif target_node.is_child(child):
                            if child.entry:
                                if __debug__:
                                    logger.debug(str.format("{0}: calling entry on: {1}", state_machine, target_node))
                                methodcalls.append(child.entry)
                            source_node = child
                            break
            else:
                if __debug__:
                    logger.debug(str.format("{0}: find child node: source_node == target_node", state_machine))

        # initial entries
        if __debug__:
            logger.debug(str.format("{0}: following initial states...", state_machine))
        if target_node.initial:
            target_node = target_node.initial
            while target_node.initial:
                if target_node.entry:
                    if __debug__:
                        logger.debug(str.format("{0}: calling entry on state: {1}", state_machine, target_node))
                    methodcalls.append(target_node.entry)
                target_node = target_node.initial
            # last node should be entered too
            if target_node.entry:
                if __debug__:
                    logger.debug(str.format("{0}: calling entry on state: {1}", state_machine, target_node))
                methodcalls.append(target_node.entry)

        if __debug__:
            logger.info(str.format("{0}: changed state from {1} to {2} using transition {3}", \
                                                                state_machine, current_state, target_node, transition))

        return guard, methodcalls, target_node

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

class SympleHFSM(object):
    """
    .. todo:: should transition.action be able to return something to the caller?
    .. todo:: should it be possible to pass in arguments for the transition action through the event handler method?

    Base state machine logic. It implements the state transition logic.

    :Parameters:
        structure : Structure
            The state machine structure of states and transitions
        actions : Actions
            The object implementing the actions interface to be used by the state machine.
        name : string
            Optional, default: None. This name will be used for logging and printing.

    .. versionadded:: 2.0.2.0
    """

    class ReentrantEventException(Exception):
        """
        Exception raised if an event is already processing.
        """
        pass

    class NotInitializedException(Exception):
        """
        Exception raised if it is attemped to process an event before
        init has been called.
        """
        pass

    class InitAlreadyCalledError(Exception):
        """
        Exception raised if init is calle more than once.
        
        .. versionadded:: 2.0.2.0
            Raised when init is called multiple times.
            
        """
        pass

    def __init__(self, structure, actions, name=None):
        self.actions = actions
        self._structure = structure
        self._current_state = None
        self._currently_handling_event = False
        self.name = str(id(self))
        if name:
            self.name = name
        self.handle_event = self._handle_event_not_inititalized

    def __str__(self):
        return str.format("<{0}[{1}]>", self.__class__.__name__, str(self.name))

    def _get_current_state(self):
        """
        Returns identifier of the current state.

        :returns: the current state identifier of the state machine or None (only if not initialized).
        
        .. versionchanged:: 2.0.2.0
            Returns a state identifier or None instead of the state instance.
        """
        return self._current_state.name if self._current_state else self._current_state

    current_state = property(_get_current_state, doc="""Current state identifier\
                    or None if the state machine is not initialized""")

    def set_state(self, state_identifier):
        """
        Set the state directly as the current state without calling
        any entry or exit or any other events on any state. Don't use it unless you need to (like initializing).
        Use with caution. Raises a 'ReentrantEventException' if it is currently processing an event. If the
        state is not known, then a 'StateUnkownError' is raised.

        :Note: No actions are called! e.g.: exit, entry, transition action are not called, use init() instead!

        :Parameters:
            state_identifier : state
                State to which current state will point afterwards.

        ..versionchanged:: 2.0.2.0
            Define the state to be set by its identifier instead of the state instance.

        :raises: StateUnknownError if there is no state defined for given state_identifier.
        :raises: ReentrantEventException if this method is called during a event is handled.
        """
        if state_identifier not in list(self._structure.states.keys()):
            raise StateUnknownError(str(state_identifier))
        if self._currently_handling_event:
            raise self.ReentrantEventException("multi threading or calling set_state from within an actions \
                                                                                during event handling is not supported")
        self._current_state = self._structure.states[state_identifier]

    def init(self, use_optimization=True):
        """
        Initialize the state machine. It descents along the 'initial' attribute of the states and sets the
        current_state accordingly.

        :Parameters:
            use_optimization : boolean
                Default: True. If set to False the event handling method will always compute the entire path
                through the structure. Otherwise if set to True and the structure has been optmized, then the
                cached transition information is used.

        :Raises:
            InitAlreadyCalledError if calle more than once.

        """
        if self.handle_event != self._handle_event_not_inititalized:
            raise self.InitAlreadyCalledError(str(self))

        node = self._structure.states[self._structure.root]
        node.check_consistency()

        while True:
            if __debug__:
                logger.debug(str.format("{0}: INIT, calling entry on {1}", self, node))
            if node.entry:
                node.entry(self.actions)
            if not node.initial:
                break
            node = node.initial

        if __debug__:
            logger.debug(str.format("{0}: INIT done, current state: {1}", self, node))
        self._current_state = node

        # set up the right event handling method bo be used
        if use_optimization and self._structure.is_optimized:
            self.handle_event = self._handle_event_optimized
            if __debug__:
                logger.info("{0}: INIT using optmized structure".format(self))
        else:
            self.handle_event = self._handle_event_normal
            if __debug__:
                logger.info("{0}: INIT not using optmized structure".format(self))

    def exit(self):
        """
        Exits the state machine. Starting from the current_state it calls exit along the parent attribute on each
        state until the root state is exited.
        """
        node = self._structure.states[self.current_state] if self.current_state else None
        while node:
            if __debug__:
                logger.debug(str.format("{0}: EXIT, calling exit on {1}", self, node))
            if node.exit:
                node.exit(self.actions)
            node = node.parent
        self._current_state = None
        self.handle_event = self._handle_event_not_inititalized

    def _handle_event_not_inititalized(self, *args):
        """
        The event handling method that gets called when the state machine is not initialized yet.
        
        :raises: NotInitializedException if init() has not been called before.
        """
        if __debug__:
            logger.debug("{0}: raising NotInitializedException".format(self))
        raise self.NotInitializedException("Call init befor any event processing!")

    def _handle_event_optimized(self, event):
        """
        The event handling method used when the structure is optimized.
        
        :raises: ReentrantEventException if this method is called while an event is handled.

        .. todo:: how to remove those checks? use queue to make those check unneeded??
        """
        if self._currently_handling_event:
            logger.info("{0}: raising ReentrantEventException".format(self))
            raise self.ReentrantEventException("multi threading or calling a event function from within an actions \
                                                                                during event handling is not supported")
        self._currently_handling_event = True
        if __debug__:
            logger.debug(str.format("{0}: _currently_handling_event 'True' {1}", self, event))

        guard, methodcalls, target_node = self._current_state.optimized[event]
        if __debug__:
            logger.debug(str.format("{0}: get_methodcallers returnded: {0} {1} {2}", \
                                                                        guard, methodcalls, target_node, self))

        if guard:
            if guard(self.actions) is False:
                if __debug__:
                    logger.info(str.format("{0}: guard of transition returned 'False', not changing state", self))
                self._currently_handling_event = False
                return
            if __debug__:
                logger.info(str.format("{0}: guard of transition returned 'True'", self))

        for methodcaller in methodcalls:
            if __debug__:
                logger.info(str.format("{0}: calling methodcaller: {1}".format(self, methodcaller)))
            methodcaller(self.actions)

        # set the new current state
        if target_node:
            if __debug__:
                logger.info(str.format("{0}: setting new state {1}".format(self, target_node)))
            self._current_state = target_node

        self._currently_handling_event = False
        if __debug__:
            logger.debug(str.format("{0}: _currently_handling_event 'False'", self))

    def _handle_event_normal(self, event):
        """
        The event handling method if the structure is not optimized, computes the way through the hierarchy.
        Handles the event and does a state change if needed. Raises a 'ReentrantEventException' if it is currently
        processing an event.

        :Parameters:
            event_func : operator.methodcaller
                A methodcaller instance pointed to the function that should be called on the state.
                For example if the method 'a' should be called on each state, then this should be
                'event_func = operator.methodcaller('a', context)'
            context : context
                the context of the state machine, where certain methods and data is
                accesible (like the actions interface).

        :raises: ReentrantEventException if this method is called while an event is handled.
        """
        if self._currently_handling_event:
            if __debug__:
                logger.info("{0}: raising ReentrantEventException".format(self))
            raise self.ReentrantEventException("multi threading or calling a event function from within an actions\
                                                                                during event handling is not supported")
        self._currently_handling_event = True
        if __debug__:
            logger.debug(str.format("{0}: _currently_handling_event 'True' {1}", self, event))

        guard, methodcalls, target_node = self._structure._get_methodcallers(self, event, self._current_state)
        if __debug__:
            logger.info(str.format("{3}; get_methodcallers returned: {0} {1} {2}", \
                                                                        guard, methodcalls, target_node, self))

        if guard:
            if guard(self.actions) is False:
                if __debug__:
                    logger.info(str.format("{0}: guard of transition returned 'False', not changing state", self))
                self._currently_handling_event = False
                logger.info(str.format("{0}: _currently_handling_event 'False' with guard", self))
                return
            if __debug__:
                logger.info(str.format("{0}: guard of transition returned 'True'", self))

        for methodcaller in methodcalls:
            if __debug__:
                logger.debug(str.format("{0}: calling methodcaller: {1}".format(self, methodcaller)))
            methodcaller(self.actions)

        # set the new current state
        logger.info(str.format("{0}: setting new state {1}".format(self, target_node)))
        self._current_state = target_node

        if __debug__:
            logger.debug(str.format("{0}: _currently_handling_event 'False'", self))
        self._currently_handling_event = False

    def handle_event(self, event):
        """
        Handles the event and does a state change if needed. Raises a 'ReentrantEventException' if it is
        currently processing an event.

        :Parameters:
            event_func : operator.methodcaller
                A methodcaller instance pointed to the function that should be called on the state.
                For example if the method 'a' should be called on each state, then this should be
                'event_func = operator.methodcaller('a', context)'
            context : context
                the context of the state machine, where certain methods and data is
                accesible (like the actions interface).

        """
        # its here for the documentation, its set in the code directly, used as a function pointer
        pass



# -----------------------------------------------------------------------------

class SympleDictHFSM(object):
    """

    .. deprecated:: 1.0.3.0 (use :class:`SympleHFSM` instead!)
    """
    pass

# just not to break existing code, will be removed in next version
# SympleDictHFSM = SympleHFSM

# -----------------------------------------------------------------------------


class BaseHFSMTests(unittest.TestCase):
    """
    Base TestCase that already defines test code for testing state machines
    build using an events and action interface
    (see: http://accu.org/index.php/journals/1548)
    """

    class RecordingActions(object):
        """
        This is a class that records the names of the functions called on it.
        Instead of writing a TestActions class, that records which action was
        activated, this class can be used. Just use the method names of the
        Action interface to compare the actually called method with the
        expected method in the tests.

        :Instancevariable:
            captured_actions : list
                List of captured method names that where called.
            args : list
                List of tuples '(args, kwargs)' in the order the action methods
                where called.
                For each action method call there is a tuple inserted.
                If no arguments are passed then a empty tuple is
                inserted, e.g. '( ( ,), ( ,) )'

        """

        def __init__(self):
            self.captured_actions = []
            self._name = None  # for internal use
            self.args = []

        def __getattr__(self, name):
            self._name = name
            return self._nop

        def _nop(self, *args, **kwargs):
            """
            This is the method that actually gets called instead of
            the real actions method. It will record the call.
            """
            self.args.append((args, kwargs))
            self.captured_actions.append(self._name)

    class TestVector(object):
        """
        A TestVector is basically the data container needed to test one
        transition.

        :Parameters:
            title : string
                Description of this TestVector
            starting_state : State
                the state from which this transition starts
            event_func : Func
                the function handling the event
            expected_state : State
                the state that should be the current_state after
                the transition
            expected_actions : list
                list of expected actions to be compared with the
                captured actions

        """

        def __init__(self,
                    title,
                    starting_state,
                    event_func,
                    expected_state,
                    expected_actions):
            self.title = title
            self.starting_state = starting_state
            self.event_func = event_func
            self.expected_state = expected_state
            self.expected_actions = expected_actions

    def prove_one_transition(self,
                            state_machine,
                            resulting_actions,
                            test_vector):
        """
        Test one transition.

        :Parameters:
            state_machine : StateMachine
                the instance of the state machine to use
            resulting_actions : Actions
                instance of the class implementing the Actions that
                captures the actions
                needs to have an attribute 'captured_actions' which is a list
                of the captured actions
            test_vector : TestVector
                the TestVector to test
        """

        state_machine.set_state(test_vector.starting_state)

        # clear the results of changing to the starting state
        resulting_actions.captured_actions = []

        test_vector.event_func()

        if len(test_vector.expected_actions) != \
                                    len(resulting_actions.captured_actions):
            self.fail("Not same number of expected and captured actions!\
                                \n expected: {0} \n \
                                captured: {1}".format( \
                                ", ".join(test_vector.expected_actions), \
                                ", ".join(resulting_actions.captured_actions)))

        for idx, expected_action in enumerate(test_vector.expected_actions):
            action = resulting_actions.captured_actions[idx]
            if action != expected_action:
                self.fail(str.format("captured action does not match with \
                        expected action! \n expected: {0} \n captured: {1}", \
                            ", ".join(test_vector.expected_actions), \
                            ", ".join(resulting_actions.captured_actions)))

        msg = "state machine not in expected state after transition, current: \
                    {0} expected: {1}".format(\
                    state_machine.current_state, test_vector.expected_state)
        self.assertTrue(test_vector.expected_state == \
                                            state_machine.current_state, msg)

        msg = "state machine ! in expected state after transition, current: \
                    {0} expected: {1}".format(\
                    state_machine.current_state, test_vector.expected_state)
        self.assertTrue(test_vector.expected_state is \
                                            state_machine.current_state, msg)

    def prove_transition_sequence(self,
                                    title,
                                    starting_state,
                                    event_funcs,
                                    expected_state,
                                    expected_actions,
                                    state_machine,
                                    resulting_actions):
        """
        Test a sequence of transitions by passing in a sequence of event and checking the actions.

        :Parameters:
            title : string
                Description of this test
            starting_state : State
                the state from which this transition starts
            event_funcs : Func
                list of event functions to call
            expected_state : State
                the state that should be the current_state after the transition
            expected_actions : list
                list of expected actions to be compared with the captured actions
            state_machine : SympleHFSM
                the statemachine to test, an instance of SympleHFSM (or inheritet class)
            resulting_actions : Actions
                the actions used for the statemachine and for this test, has to have an attribute 'captured_actions'
        """
        state_machine.set_state(starting_state)

        # clear the results of changing to the starting state
        resulting_actions.captured_actions = []

        for event_func in event_funcs:
            event_func()

        if len(expected_actions) != len(resulting_actions.captured_actions):
            self.fail(str.format("Not same number of expected and captured actions! \n \
                                    expected: {0} \n \
                                    captured: {1}", \
                                    ", ".join(expected_actions), \
                                    ", ".join(resulting_actions.captured_actions)))

        for idx, expected_action in enumerate(expected_actions):
            action = resulting_actions.captured_actions[idx]
            if action != expected_action:
                self.fail(str.format("captured action does not match with expected action! \n \
                                        expected: {0} \n \
                                        captured: {1}", \
                                    ", ".join(expected_actions), \
                                    ", ".join(resulting_actions.captured_actions)))

        msg = "state machine not in expected state after transition, current: {0} expected: {1}".format(\
                                                                    state_machine.current_state, expected_state)
        self.assertTrue(expected_state == state_machine.current_state, msg)

        msg = "state machine ! in expected state after transition, current: {0} expected: {1}".format(\
                                                                    state_machine.current_state, expected_state)
        self.assertTrue(expected_state is state_machine.current_state, msg)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

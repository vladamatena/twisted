# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Test cases for L{twisted.python.logger._legacy}.
"""

import logging as py_logging

from zope.interface.verify import verifyObject, BrokenMethodImplementation

from twisted.trial import unittest

from twisted.python import log as twistedLogging
from twisted.python.failure import Failure
from twisted.python.log import LogPublisher as OldLogPublisher

from .._levels import LogLevel
from .._observer import ILogObserver
from .._legacy import LegacyLogObserverWrapper
from .._format import formatEvent



class LegacyLogObserverWrapperTests(unittest.TestCase):
    """
    Tests for L{LegacyLogObserverWrapper}.
    """

    def test_interface(self):
        """
        L{LegacyLogObserverWrapper} is an L{ILogObserver}.
        """
        legacyObserver = lambda e: None
        observer = LegacyLogObserverWrapper(legacyObserver)
        try:
            verifyObject(ILogObserver, observer)
        except BrokenMethodImplementation as e:
            self.fail(e)


    def test_repr(self):
        """
        L{LegacyLogObserverWrapper} returns the expected string.
        """
        class LegacyObserver(object):
            def __repr__(self):
                return "<Legacy Observer>"

            def __call__(self):
                return

        observer = LegacyLogObserverWrapper(LegacyObserver())

        self.assertEquals(
            repr(observer),
            "LegacyLogObserverWrapper(<Legacy Observer>)"
        )


    def observe(self, event):
        """
        Send an event to a wrapped legacy observer.

        @param event: an event
        @type event: L{dict}

        @return: the event as observed by the legacy wrapper
        """
        events = []

        legacyObserver = lambda e: events.append(e)
        observer = LegacyLogObserverWrapper(legacyObserver)
        observer(event)
        self.assertEquals(len(events), 1)

        return events[0]


    def forwardAndVerify(self, event):
        """
        Send an event to a wrapped legacy observer and verify that its data is
        preserved.

        @param event: an event
        @type event: L{dict}

        @return: the event as observed by the legacy wrapper
        """
        # Send a copy: don't mutate me, bro
        observed = self.observe(dict(event))

        # Don't expect modifications
        for key, value in event.items():
            self.assertIn(key, observed)
            self.assertEquals(observed[key], value)

        return observed


    def test_forward(self):
        """
        Basic forwarding.
        """
        self.forwardAndVerify(dict(foo=1, bar=2))


    def test_system(self):
        """
        Translate: C{"log_system"} -> C{"system"}
        """
        event = self.forwardAndVerify(dict(log_system="foo"))
        self.assertEquals(event["system"], "foo")


    def test_pythonLogLevel(self):
        """
        Python log level is added.
        """
        event = self.forwardAndVerify(dict(log_level=LogLevel.info))
        self.assertEquals(event["logLevel"], py_logging.INFO)


    def test_message(self):
        """
        C{"message"} key is added.
        """
        event = self.forwardAndVerify(dict())
        self.assertEquals(event["message"], ())


    def test_format(self):
        """
        Formatting is translated properly.
        """
        event = self.forwardAndVerify(
            dict(log_format="Hello, {who}!", who="world")
        )
        self.assertEquals(
            twistedLogging.textFromEventDict(event),
            b"Hello, world!"
        )


    def test_failure(self):
        """
        Failures are handled, including setting isError and why.
        """
        failure = Failure(RuntimeError("nyargh!"))
        why = "oopsie..."
        event = self.forwardAndVerify(dict(
            log_failure=failure,
            log_format=why,
        ))
        self.assertIdentical(event["failure"], failure)
        self.assertTrue(event["isError"])
        self.assertEquals(event["why"], why)



class TestOldLogPublisher(unittest.TestCase):
    """
    L{OldLogPublisher} constructs old-style log events and then adds the
    necessary new-style keys.
    """

    def setUp(self):
        """
        Create an L{OldLogPublisher} and a log observer to catch its output.
        """
        self.events = []
        self.old = OldLogPublisher(self.events.append, self.events.append)


    def test_simple(self):
        """
        Messages with a simple message are translated such that the readable
        message remains the same.
        """
        self.old.msg("Hello world.")
        self.assertEquals(len(self.events), 1)
        self.assertEquals(formatEvent(self.events[0]), "Hello world.")
        self.assertEquals(self.events[0]['log_level'], LogLevel.info)


    def test_errorSetsLevel(self):
        """
        Setting the old-style 'isError' key will result in the emitted message
        acquiring the 'isError' key.
        """
        self.old.msg(isError=True)
        self.assertEquals(len(self.events), 1)
        self.assertEquals(self.events[0]['log_level'], LogLevel.critical)


    def test_oldStyleLogLevel(self):
        """
        Setting the old-style 'logLevel' key will result in the emitted message
        acquiring the new-style 'log_level' key.
        """
        self.old.msg(logLevel=py_logging.WARNING)
        self.assertEquals(len(self.events), 1)
        self.assertEquals(self.events[0]['log_level'], LogLevel.warn)

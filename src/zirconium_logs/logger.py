""" Provides an improved logging class with audit(), trace() and out(). """
import logging


class ImprovedLogger(logging.getLoggerClass()):
    """ An extension of the base logger that adds methods for our custom logging levels """

    def audit(self, message, *args, **kwargs):
        """ Log an audit event; this is intended to be used by an audit hook. """
        if self.isEnabledFor(1):
            self.log(1, message, *args, **kwargs)

    def trace(self, message, *args, **kwargs):
        """ Tracing provides very-low level details that may rarely be pertinent. """
        if self.isEnabledFor(5):
            self.log(5, message, *args, **kwargs)

    def out(self, message, *args, **kwargs):
        """ An output message is intended to be a step above info and a step below warning, to show status messages
            to the user
        """
        if self.isEnabledFor(25):
            self.log(25, message, *args, **kwargs)

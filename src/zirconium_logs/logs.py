""" Logging management compatible with Zirconium with additional features"""
from autoinject import injector
import zirconium as zr
import logging.config
import logging
import threading
import queue
import sys
import atexit
import time


class AuditLog(threading.Thread):
    """ Responsible for managing a queue of audit messages from sys.audit() and passing them to the logging.

        Note that this is necessary because calls directly to logging.audit() will cause an error, so we will
        manage them in a thread instead.

        :param omit_logging_frames: If set to false, all sys._getframe events will be logged. If set to true (the
            default), sys._getframe events from the logging.__init__ file are ignored (these are commonly related to
            using the logging subsystem itself and clutter up the logs)
        :type omit_logging_frames: bool
    """

    def __init__(self, omit_logging_frames=True):
        self._write_queue = queue.SimpleQueue()
        self.omit_logging_frames = omit_logging_frames
        self._halt = False
        self.log = logging.getLogger("sys.audit")
        self.lock = threading.Lock()
        super().__init__()
        self.daemon = True

    def halt(self):
        """ Stops the thread by setting the _halt flag and then joining. """
        self._halt = True
        self.join()

    def audit_hook(self, action, info):
        """ Audit hook for sys.addaudithook() that queues the message to be sent. """
        if not self._halt:
            s = "{}: {}".format(action, ";".join(str(x) for x in info))
            # sys._getframe is called a lot when logging, so this prevents a lot of junk from the logging module
            if (not self.omit_logging_frames) or not (action == "sys._getframe" and ("logging\\\\__init__.py" in s or "logging/__init__.py" in s)):
                self._write_queue.put(s)

    def run(self):
        """ Implementation of run() """
        while True:
            try:
                nxt = self._write_queue.get(True, 0.1)
                self.log.audit(nxt)
            except queue.Empty as ex:
                # Check for _halt here to make sure that the queue is empty when we halt
                if self._halt:
                    break
                # Give ourselves a bit of a break
                time.sleep(0.01)


@zr.configure
def config_logging(config: zr.ApplicationConfig):
    """ Configuration for zirconium """
    config.register_file("~/.logging.toml")
    config.register_file("./.logging.toml")


def _add_logging_level(level_name, level_no):
    """ Adds a logging level """

    def log_at_level(message, *args, **kwargs):
        logging.log(level_no, message, *args, **kwargs)

    level_name = level_name.upper()
    method_name = level_name.lower()
    logging.addLevelName(level_no, level_name)
    setattr(logging, level_name, level_no)
    setattr(logging, method_name, log_at_level)


@injector.inject
def init_logging(config: zr.ApplicationConfig):
    """ Initializes logging from the configuration file as well as adding our custom levels and, if specified, audit
        output
    """
    # Audit is for the sys.audit(), if enabled
    _add_logging_level("AUDIT", 1)
    # Trace is a lower level than debug for even more information
    _add_logging_level("TRACE", 5)
    # Out is a level higher than info but lower than warning for what a CLI user might want to see
    _add_logging_level("OUT", 25)
    # Import is done here in case something else has overridden the default logging class
    from .logger import ImprovedLogger
    logging.setLoggerClass(ImprovedLogger)
    if "logging" in config:
        # Load our logging configuration
        logging.config.dictConfig(config["logging"])
        # If we want to include audit events, set up the logging for them
        if config.as_bool(("logging", "with_audit"), False):
            audit_logger = AuditLog(config.as_bool(("logging", "omit_logging_frames"), True))
            audit_logger.start()
            sys.addaudithook(audit_logger.audit_hook)
            atexit.register(audit_logger.halt)

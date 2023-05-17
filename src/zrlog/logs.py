""" Logging management compatible with Zirconium with additional features"""
from autoinject import injector
import zirconium as zr
import logging.config
from zrlog.logger import ImprovedLogger, _LogSettingManager
import logging
import threading
import queue
import sys
import atexit
import os


class AuditLog(threading.Thread):
    """ Responsible for managing a queue of audit messages from sys.audit() and passing them to the logging.

        Note that this is necessary because calls directly to logging.audit() will cause an error, so we will
        manage them in a thread instead.

        :param omit_logging_frames: If set to false, all sys._getframe events will be logged. If set to true (the
            default), sys._getframe events from the logging.__init__ file are ignored (these are commonly related to
            using the logging subsystem itself and clutter up the logs)
        :type omit_logging_frames: bool
    """

    def __init__(self, omit_logging_frames=True, log_level="AUDIT"):
        self._write_queue = queue.SimpleQueue()
        self.omit_logging_frames = omit_logging_frames
        self._halt = threading.Event()
        self.log = logging.getLogger("sys.audit")
        self._log_level_cb = self.log.audit
        if (not log_level == "AUDIT") and hasattr(self.log, log_level.lower()):
            self._log_level_cb = getattr(self.log, log_level.lower())
        self.lock = threading.Lock()
        super().__init__()
        self.daemon = True

    def halt(self):
        """ Stops the thread by setting the _halt flag and then joining. """
        self._halt.set()
        self.join()

    def audit_hook(self, action, info):
        """ Audit hook for sys.addaudithook() that queues the message to be sent. """
        if not self._halt.is_set():
            s = "{}: {}".format(action, ";".join(str(x) for x in info))
            # sys._getframe is called a lot when logging, so this prevents a lot of junk from the logging module
            if (not self.omit_logging_frames) or not (action == "sys._getframe" and ("logging\\\\__init__.py" in s or "logging/__init__.py" in s)):
                self._write_queue.put(s)

    def run(self):
        """ Implement of run() """
        while not self._halt.is_set():
            try:
                self._log_level_cb(self._write_queue.get(False))
            except queue.Empty as ex:
                pass
                # Give ourselves a bit of a break
                self._halt.wait(0.1)
        while not self._write_queue.empty():
            self._log_level_cb(self._write_queue.get(False))


@zr.configure
def config_logging(config: zr.ApplicationConfig):
    """ Configuration for zirconium """
    config.register_file("~/.logging.toml")
    config.register_file("./.logging.toml")
    custom_path = os.environ.get("ZRLOG_CONFIG_FILE")
    if custom_path:
        config.register_file(custom_path)


def get_logger(name: str) -> ImprovedLogger:
    _LogSettingManager.get().init()
    return logging.getLogger(name)


@injector.inject
def init_logging(config: zr.ApplicationConfig = None):
    """ Initializes logging from the configuration file as well as adding our custom levels and, if specified, audit
        output
    """
    # Add the additional logging levels
    instance = _LogSettingManager.get()
    instance.init()
    if "logging" in config:
        # Load our logging configuration
        logging.config.dictConfig(config["logging"])
        # If we want to include audit events, set up the logging for them
        if config.as_bool(("logging", "with_audit"), False) and sys.version_info.major >= 3 and sys.version_info.minor >= 8:
            audit_logger = AuditLog(
                config.as_bool(("logging", "omit_logging_frames"), True),
                config.as_str(("logging", "audit_level"), "AUDIT")
            )
            audit_logger.start()
            sys.addaudithook(audit_logger.audit_hook)
            atexit.register(audit_logger.halt)
        # Load defaults for extras
        instance.set_defaults(config.as_dict(("logging", "default_extras"), default={}))
        # Load stack trace visibility setting
        instance.show_stack_traces = config.as_bool(("logging", "show_stack_traces"), default=True)
    logging.getLogger("zrlog").debug("Zirconium-based logging initialized")

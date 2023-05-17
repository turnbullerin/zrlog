""" Provides an improved logging class with audit(), trace() and out(). """
import logging
import contextvars
import typing as t
import threading
import copy


_logging_context_extras = contextvars.ContextVar[dict]("zrlog_extra_vars", default=None)


class _LogSettingManager:
    """Manage the global settings for the logger."""

    instance = None
    lock = threading.Lock()

    def __init__(self):
        self.logging_defaults = {}
        self.logging_defaults_lock = threading.Lock()
        self.show_stack_traces = True
        self.has_been_init = False

    def init(self):
        if not self.has_been_init:
            # Audit is for the sys.audit(), if enabled
            self._add_logging_level("AUDIT", 1)
            # Trace is a lower level than debug for even more information
            self._add_logging_level("TRACE", 5)
            # For output to users that needs logging (for CLI)
            self._add_logging_level("OUT", 25)
            # Notice is for things that are normal conditions but require auditing
            self._add_logging_level("NOTICE", 27)
            # Import is done here in case something else has overridden the default logging class
            logging.setLoggerClass(ImprovedLogger)
            self.has_been_init = True

    def _add_logging_level(self, level_name, level_no):
        """ Adds a logging level """

        def log_at_level(message, *args, **kwargs):
            logging.log(level_no, message, *args, **kwargs)

        level_name = level_name.upper()
        method_name = level_name.lower()
        logging.addLevelName(level_no, level_name)
        setattr(logging, level_name, level_no)
        setattr(logging, method_name, log_at_level)

    def set_default(self, key: str, default_value: t.Any):
        with self.logging_defaults_lock:
            self.logging_defaults[key] = default_value

    def set_defaults(self, defaults: dict):
        with self.logging_defaults_lock:
            self.logging_defaults.update(defaults)

    def set_logging_extra(self, name: str, val: t.Any):
        self.set_logging_extras({name: val})

    def set_logging_extras(self, extras: dict):
        d = _logging_context_extras.get()
        if d is None:
            d = {}
        d.update(extras)
        _logging_context_extras.set(d)

    def get_logging_extras(self):
        d = _logging_context_extras.get()
        if d is None:
            return self.logging_defaults
        elif not self.logging_defaults:
            return d
        else:
            base = copy.copy(self.logging_defaults)
            base.update(d)
            return base

    @staticmethod
    def get():
        if _LogSettingManager.instance is None:
            with _LogSettingManager.lock:
                if _LogSettingManager.instance is None:
                    _LogSettingManager.instance = _LogSettingManager()
        return _LogSettingManager.instance


def set_default_extra(name: str, val: t.Any = ''):
    """Set a default value for a logging extra"""
    _LogSettingManager.get().set_default(name, val)


def set_show_stack_trace(show_stack_traces: bool):
    """Set whether or not to show stack traces"""
    _LogSettingManager.get().show_stack_traces = show_stack_traces


def set_extra(name: str, val: t.Any):
    """Set a logging extra variable"""
    _LogSettingManager.get().set_logging_extra(name, val)


def set_extras(extras: dict):
    """Set more than one logging extra variable"""
    _LogSettingManager.get().set_logging_extras(extras)


class ImprovedLogger(logging.getLoggerClass()):
    """ An extension of the base logger that adds methods for our custom logging levels """

    def _log(self, *args, **kwargs):
        extras = {}
        if len(args) >= 5:
            extras = args[4]
        elif "extra" in kwargs:
            extras = kwargs["extra"]
        else:
            kwargs["extra"] = extras
        extras.update(_LogSettingManager.get().get_logging_extras())
        return super()._log(*args, **kwargs)

    def exception(self, *args, **kwargs):
        if _LogSettingManager.get().show_stack_traces:
            super().exception(*args, **kwargs)
        else:
            self.error(*args, **kwargs)

    def audit(self, message, *args, **kwargs):
        """ Log an audit event; this is intended to be used by an audit hook. """
        if self.isEnabledFor(1):
            self.log(1, message, *args, **kwargs)

    def trace(self, message, *args, **kwargs):
        """ Log a TRACE level log; this is intended for very fine-grained details below DEBUG. """
        if self.isEnabledFor(5):
            self.log(5, message, *args, **kwargs)

    def out(self, message, *args, **kwargs):
        """ Log an OUT level log; this is intended for user output that should also be logged. """
        if self.isEnabledFor(25):
            self.log(25, message, *args, **kwargs)

    def notice(self, message, *args, **kwargs):
        """ Log a NOTICE level log; this is intended for a normal condition that requires capturing in production. """
        if self.isEnabledFor(27):
            self.log(27, message, *args, **kwargs)

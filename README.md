# Zirconium Logging (ZrLog)
This package adds logging support using the Zirconium configuration tool and TOML, with an extension for supporting
logging audit events.


## Defining Logging Parameters
Configuration for the logging module can be added in TOML under the `logging` key. The entries correspond to those 
supported by `logging.config.dictConfig()` with a few additions to support audit logging. For example:

    # .logging.toml (or your own app configuration file that you've registered) 
    [logging]
    version = 1

    [logging.root]
    level = "INFO"
    handlers = ["console"]

    [logging.handlers.console]
    class = "logging.StreamHandler"
    formatter = "brief"
    level = "WARNING"
    stream = "ext://sys.stdout"

    [logging.formatters.brief]
    format = "%(message)s [%(levelname)s]"


Of note, if you want to change a specific logger (which often have dots in the name), you must quote the key:

    [logging.loggers."module.foo.bar"]
    level = "WARNING"


## Additional Logging Levels
This package adds three additional levels of logging:

- audit(), which is intended to be used only with the Python auditing system as described below. The logging level is 
  set to 1.
- trace(), which is intended to be even more detailed than debug(). The logging level is set to 5.
- out(), which is ranked between INFO and WARNING and is intended to be used to log user output for command-line 
  applications. The logging level is set to 25.

These are configured as methods on the `getLogger()` class as well as on `logging` itself for the root logger.


## Logging Audit Events
This package provides a system for turning `sys.audit()` events into log records using a thread-based queue. This is 
necessary because audit events don't play nicely with the logging subsystem, leading to inconsistent errors if the
logger `log()` method is called directly from the audit hook. Audit logging must be enabled specifically by setting
the with_audit flag:

    # .logging.toml
    [logging]
    with_audit = true

One specific event can cause further problems: sys._getframe() is called repeatedly from the logging subsystem in Python
(in 3.8 at least). These audit events are NOT logged by default, but logging of them can be enabled by turning off the
`omit_logging_frames` flag.

    # .logging.toml
    [logging]
    with_audit = true
    omit_logging_frames = false

Audit events are logged at the AUDIT level which is below TRACE; your logger and handler must be set to that level to 
see these events:

    [logging.root]
    level = "AUDIT"
    handlers = ["console"]

    [logging.handlers.console]
    class = "logging.StreamHandler"
    formatter = "brief"
    level = "AUDIT"
    stream = "ext://sys.stdout"

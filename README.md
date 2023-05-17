# Zirconium Logging (ZrLog)
Logging configuration is often complex and Python is missing a few "nice" features that exist in 
other languages logging systems. This package hopes to simplify the experience of configuring logging while adding a few
nice features:

* Loading logging configuration from TOML or YAML (via `zirconium`) instead of the older `configparser` format
* `TRACE` level for very fine-grained output (more so that `DEBUG`)
* `NOTICE` level for normal conditions that should always be output
* `OUT` level for logging user messages
* `AUDIT` level for interacting with Python's audit hooks
* A threaded audit hook that logs most audit messages
* The ability to disable stack trace output
* The ability to set context-specific "extra" variables on all loggers and to provide defaults for these
  so that they can be added to all logging messages within that context (e.g. for usernames)

## Basic Usage

```python 
# Do this at the start of any run of your code
import zrlog

# Imports logging configuration from TOML and sets up the logging system for you.
zrlog.init_logging()

# Set a default username
zrlog.set_default_extra('username', '**anonymous**')

# logging.getLogger() works as well, this version is a wrapper that (a) makes sure that `zrlog.init_logging()` was 
# called and (b) provides a better type hint for the logger class.
logger = zrlog.get_logger(__name__)
```

## Configuration File
By default, logging configuration comes from a TOML file in up to three places:

* `[HOME_DIRECTORY]/.logging.toml`
* `[CURRENT_WORKING_DIRECTORY]/.logging.toml`
* Value of the `ZRLOG_CONFIG_FILE` environment variable. This file may also be a YAML or other formats supported by 
  `zirconium`
  
If you use `zirconium` for your project configuration, it can also be in any configuration file specified by your
project.
  
The logging configuration file is similar to that defined by `logging.config.dictConfig()`, with a few extensions. See 
the `.logging.example.toml` file for configuration.


## Performance impact
Testing suggests that the impact of replacing the typical `logging` approach with this module is about 14% slower to 
get a logger and 10% slower to make a logging call with extras. However, the time to make a log to `stdout` is 
still only 0.013 ms (compared to 0.012 ms for the standard logging package), therefore this performance impact is 
probably insignificant in most use cases.

## Log Level Recommendations
| Level | Use Case |
| --- | --- |
| critical | An error so severe has occurred that the application may now crash. |
| error | An error has occurred and may have created unexpected behaviour. |
| warning | Something unexpected happen but it is recoverable, or a problem may occur in the future. |
| notice | Something expected has happened that needs to be tracked in a production environment (e.g. user login). |
| out | Something expected has happened in a command line environment that the user needs to be notified of. |
| info | Something expected has happened that does not need tracking but can be useful to confirm normal operation. |
| debug | Additional detail for debugging an issue |
| trace | Even more detail for debugging an issue |
| audit | Python auditing output only |


## Logging Audit Events
This package provides a system for turning `sys.audit()` events into log records using a thread-based queue. This is 
necessary because audit events don't play nicely with the logging subsystem, leading to inconsistent errors if the
logger `log()` method is called directly from the audit hook. Audit logging must be enabled specifically by setting
the `with_audit` flag:

```toml
# .logging.toml
[logging]
with_audit = true
```

While the default level is "AUDIT", you can change this to any of the logging level prefixes by specifying the 
audit_level:

```toml
# .logging.toml
[logging]
with_audit = true
audit_level = "INFO"
```

One specific event can cause further problems: `sys._getframe()` is called repeatedly from the logging subsystem in Python
(in 3.8 at least). These audit events are NOT logged by default, but logging of them can be enabled by turning off the
`omit_logging_frames` flag.

```toml
# .logging.toml
[logging]
with_audit = true
omit_logging_frames = false
```

Audit events are logged (by default) at the AUDIT level which is below TRACE; your logger and handler must be set to that level to 
see these events:

```toml
[logging.root]
level = "AUDIT"
handlers = ["console"]

[logging.handlers.console]
class = "logging.StreamHandler"
formatter = "brief"
level = "AUDIT"
stream = "ext://sys.stdout"
```

## Change Log

### version 0.3.0
- Added logger extra handling via `set_logger_extra` and `set_default_logger_extra`
- Added the `NOTICE` level to correspond with more typical usage. `OUT` should be used for user output where it needs
  to be logged and `NOTICE` for normal conditions that need to be logged even in production.

### version 0.2.0
- Updated the audit handling thread to use a `threading.Event` to end itself rather than a boolean flag.
- Added the `no_config` flag, mostly to be used in test suites to ensure everything still works properly.
- Several documentation cleanup items
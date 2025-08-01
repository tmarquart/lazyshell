# lazyshell

Lazy optional imports for Python projects. `shell_import` lets you declare optional dependencies once and load them on first use. Missing packages can degrade gracefully using **sink** proxies so your code keeps running.

## Installation

```bash
pip install lazyshell
```

Supports Python 3.9 and newer and has no runtime dependencies.

## Quick start

```python
from lazyshell import shell_import

# request multiple modules at once
np, hass, missing = shell_import(
    "numpy",
    ("hass", "homeassistant.core"),
    "not_installed",
    sink=True,                      # return sink proxies for missing packages
    sink_map={"hass.log": print},  # route hass.log -> print
)

# modules are imported on first use
arr = np.arange(3)

# sink proxies are truthy and return None by default
missing.anything()  # -> None

# override behaviour for a specific attribute
hass.log("hello")  # prints "hello"
```

## Proxy behaviour

* `bool(proxy)` is `False` until the real module or object is successfully imported.
* Accessing an attribute or calling the proxy triggers the import.
* If the import fails:
  * with `sink=False` (default) a ``MissingPackage`` sentinel is returned and attribute access raises ``ImportError``.
  * with `sink=True` a ``SinkProxy`` is returned. It is truthy, attribute access returns further sink proxies and method calls are no-ops unless a fallback is provided via ``set``.
* The `.with_sink()` helper enables sink mode on creation; `.enable_sink()` enables it after a failed import.
* Register fallbacks with `proxy.set("attr", value)` or via attribute proxies: `proxy.attr.set(value)`.
* The `is_loaded` property reports whether the underlying import has occurred.

Set the environment variable `LAZYSHELL_DEBUG=1` to get a one-time warning when a sink proxy is instantiated.

## License

lazyshell is distributed under the terms of the MIT License. See `LICENSE` for details.

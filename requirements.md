Below is a drop-in requirements.md draft you can commit as-is.
(Feel free to rename or trim the front-matter section titles to match your repo style.)

⸻

lazy_shell – Requirements v0.1.0 (Alpha)

Purpose – Provide lazy, optional imports for Python projects so scripts can declare dependencies once, avoid startup cost, and degrade gracefully when a package is absent.

⸻

1. Scope

In-Scope	Out-of-Scope (future)
Lazy loading of modules/objects	Automatic pip install of missing packages
Graceful fallback “sinks” on missing imports	Mandatory/required imports that raise immediately
User-defined aliasing & dotted-path resolution	IDE-time static analysis / stub generation
Pure-stdlib implementation (3.9+)	Non-stdlib dependencies


⸻

2. Public API

from lazy_shell import shell_import

np, hass = shell_import(
    "numpy",                         # → alias `np`
    ("hass", "homeassistant.core"),  # explicit alias
    sink=True,                       # enable graceful degradation
    sink_map={"hass.log": print}     # route hass.log → print
)

shell_import(...) → tuple[Any, …]

Parameter	Type	Default	Description
*modules	str | tuple[str, str]	—	Dotted import paths, optionally paired with an alias (alias, path).
sink	bool	False	If True, failed imports return a SinkProxy (truthy, no-op). If False, they produce a MissingPackage sentinel (falsey, raises on use).
sink_map	dict[str, Any] | None	None	Maps fully qualified attribute paths to concrete fallbacks (e.g. "hass.log": print). Ignored when sink=False.

Returned proxies preserve the order of modules.

⸻

3. Runtime Behaviour

Feature	LazyModuleProxy (success)	MissingPackage (sink=False)	SinkProxy (sink=True)
Truthiness (bool(proxy))	False before first real import, True after	False	True (always)
Attribute access	Triggers first import, then forwards	Raises ImportError	Returns another SinkProxy or mapped fallback
Method call	Executes real obj	Raises ImportError	No-op (returns None) unless overridden
__repr__	<lazy_shell.Proxy numpy ...>	<lazy_shell.Missing homeassistant.core>	<lazy_shell.Sink homeassistant.core>
Thread safety	Import guarded by lock	n/a	n/a

Debugging

Set environment variable LAZYSHELL_DEBUG=1 to emit a one-time warnings.warn when the first SinkProxy is instantiated.

⸻

4. Internal Design

Class	Responsibility
_ImportSpec	Dataclass: alias, module path, attr chain list
_LazyModuleProxy	On-demand import & caching; thread-safe
_MissingPackage	Falsey sentinel; raises on any attribute/method use
_SinkProxy	Truthy stand-in; fabricates chainable proxies & no-op callables
_SinkFunction	Wrapper so mapped fallbacks keep __name__ / __doc__

All reside in lazy_shell/core.py; lazy_shell/__init__.py re-exports shell_import.

⸻

5. Edge Cases
	•	Deep attribute paths ("pkg.mod.Class.attr") fully supported.
	•	Mixing successful imports, sentinels, and sinks in one call works.
	•	Proxies are not picklable (documented limitation).

⸻

6. Packaging

Item	Spec
Package name	lazy_shell
Version	0.1.0 (Semantic Versioning)
License	MIT
Python	3.9 – 3.12
Dependencies	none (stdlib only)
Distribution layout	src/lazy_shell/, tests/, README.md, CHANGELOG.md
CI	GitHub Actions: pytest, flake8 across 3.9-3.12


⸻

7. Testing Matrix (pytest)

Category	Cases
Lazy import	Access np.sqrt loads once; repeat call skips import
Missing (sink=False)	Proxy is falsey; attr access raises ImportError
Missing (sink=True)	Proxy truthy; chained hass.foo.bar() returns None
sink_map override	"hass.log": print routes to stdout
Threaded access	Two threads call same proxy simultaneously → single import
Truthiness flips	LazyModuleProxy pre/post import behaviour verified


⸻

8. Future Roadmap
	1.	auto_install=True flag (pip install on demand, opt-in).
	2.	Context manager for bulk import + summary report.
	3.	Introspection helpers (proxy.__lazy_loaded__, etc.).
	4.	Jupyter extension to show unresolved sinks in UI.

⸻

Status: Final requirements locked. Implementation may proceed.
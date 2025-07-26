from __future__ import annotations

import importlib
import os
import threading
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Tuple

__all__ = [
    "shell_import",
    "_ImportSpec",
    "_LazyModuleProxy",
    "_MissingPackage",
    "_SinkProxy",
]


@dataclass
class _ImportSpec:
    alias: str
    path: str


_UNSET = object()
_warned = False


class _MissingPackage:
    """Sentinel for a missing optional dependency."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return False

    def __getattr__(self, item: str) -> Any:
        raise ImportError(f"Optional dependency '{self._name}' is not installed")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise ImportError(f"Optional dependency '{self._name}' is not installed")

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<lazy_shell.Missing {self._name}>"


class _SinkFunction:
    """Wrapper so mapped fallbacks keep their metadata."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self._func = func
        self.__name__ = getattr(func, "__name__", "sink")
        self.__doc__ = getattr(func, "__doc__", None)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._func(*args, **kwargs)


class _SinkProxy:
    """Truthy stand-in for missing imports."""

    def __init__(self, qualname: str, sink_map: Dict[str, Any] | None = None) -> None:
        global _warned
        if not _warned and os.getenv("LAZYSHELL_DEBUG") == "1":
            warnings.warn("lazy_shell: using sink proxy for missing import")
            _warned = True
        self._qualname = qualname
        self._sink_map = sink_map or {}

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return True

    def _lookup(self, name: str) -> Any | None:
        return self._sink_map.get(name)

    def __getattr__(self, item: str) -> Any:
        qname = f"{self._qualname}.{item}" if self._qualname else item
        fallback = self._lookup(qname)
        if fallback is not None:
            if callable(fallback):
                return _SinkFunction(fallback)
            return fallback
        return _SinkProxy(qname, self._sink_map)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        fallback = self._lookup(self._qualname)
        if callable(fallback):
            return fallback(*args, **kwargs)
        return None

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<lazy_shell.Sink {self._qualname}>"


class _LazyModuleProxy:
    """Proxy that lazily loads a module/object on first use."""

    def __init__(self, spec: _ImportSpec, sink: bool, sink_map: Dict[str, Any] | None) -> None:
        self._spec = spec
        self._sink = sink
        self._sink_map = sink_map or {}
        self._lock = threading.Lock()
        self._obj: Any = _UNSET

    def _load(self) -> Any:
        if self._obj is not _UNSET:
            return self._obj
        with self._lock:
            if self._obj is not _UNSET:
                return self._obj
            parts = self._spec.path.split(".")
            for i in range(len(parts), 0, -1):
                module_path = ".".join(parts[:i])
                try:
                    module = importlib.import_module(module_path)
                except ModuleNotFoundError:
                    continue
                obj: Any = module
                for attr in parts[i:]:
                    obj = getattr(obj, attr)
                self._obj = obj
                return obj
            if self._sink:
                self._obj = _SinkProxy(self._spec.alias, self._sink_map)
            else:
                self._obj = _MissingPackage(self._spec.alias)
            return self._obj

    def __getattr__(self, item: str) -> Any:
        return getattr(self._load(), item)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._load()(*args, **kwargs)

    def __bool__(self) -> bool:
        if self._obj is _UNSET:
            return True if self._sink else False
        return bool(self._load())

    def __repr__(self) -> str:  # pragma: no cover - trivial
        state = "loaded" if self._obj is not _UNSET else "pending"
        return f"<lazy_shell.Proxy {self._spec.path} ({state})>"


def _parse_specs(modules: Iterable[str | Tuple[str, str]]) -> Iterable[_ImportSpec]:
    for mod in modules:
        if isinstance(mod, tuple):
            alias, path = mod
        else:
            alias, path = mod.split(".")[0], mod
        yield _ImportSpec(alias=alias, path=path)


def shell_import(*modules: str | Tuple[str, str], sink: bool = False, sink_map: Dict[str, Any] | None = None) -> Tuple[Any, ...]:
    """Return proxies for the requested modules or objects."""

    specs = list(_parse_specs(modules))
    proxies = [
        _LazyModuleProxy(spec, sink=sink, sink_map=sink_map) for spec in specs
    ]
    return tuple(proxies)

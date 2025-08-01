from __future__ import annotations

import importlib
import os
import threading
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple, Union

__all__ = [
    "shell_import",
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
        return f"<lazyshell.Missing {self._name}>"


class _SinkFunction:
    """Wrapper so mapped fallbacks keep their metadata."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self._func = func
        self.__name__ = getattr(func, "__name__", "sink")
        self.__doc__ = getattr(func, "__doc__", None)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._func(*args, **kwargs)


class _AttrProxy:
    """Proxy for attributes accessed before a module is loaded."""

    def __init__(self, root: "_LazyModuleProxy", path: str) -> None:
        self._root = root
        self._path = path

    def set(self, fallback: Any) -> "_AttrProxy":
        self._root._sink_map[f"{self._root._spec.alias}.{self._path}"] = fallback
        return self

    def _resolve(self) -> Any:
        obj = self._root._load()
        for part in self._path.split("."):
            obj = getattr(obj, part)
        return obj

    def __getattr__(self, item: str) -> Any:
        return _AttrProxy(self._root, f"{self._path}.{item}")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._resolve()(*args, **kwargs)

    def __bool__(self) -> bool:
        return bool(self._resolve())

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<lazyshell.AttrProxy {self._path}>"


class _SinkProxy:
    """Truthy stand-in for missing imports."""

    def __init__(self, qualname: str, sink_map: Dict[str, Any] | None = None) -> None:
        global _warned
        if not _warned and os.getenv("LAZYSHELL_DEBUG") == "1":
            warnings.warn("lazyshell: using sink proxy for missing import")
            _warned = True
        self._qualname = qualname
        self._sink_map = sink_map or {}

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return True

    def set(self, fallback: Any) -> "_SinkProxy":
        self._sink_map[self._qualname] = fallback
        return self

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
        return f"<lazyshell.Sink {self._qualname}>"


class _LazyModuleProxy:
    """Proxy that lazily loads a module/object on first use."""

    def __init__(
        self,
        spec: _ImportSpec,
        *,
        sink: bool = False,
        sink_map: Dict[str, Any] | None = None,
    ) -> None:
        self._spec = spec
        self._sink = sink
        self._sink_map: Dict[str, Any] = sink_map or {}
        self._lock = threading.Lock()
        self._obj: Any = _UNSET
        self._available=False

    # public API -----------------------------------------------------

    def with_sink(self) -> "_LazyModuleProxy":
        """Enable sink fallback and return ``self``."""

        self._sink = True
        return self

    def enable_sink(self) -> "_LazyModuleProxy":
        """Enable sink mode for an already created proxy."""

        if not self._sink:
            self._sink = True
        if isinstance(self._obj, _MissingPackage):
            self._obj = _SinkProxy(self._spec.alias, self._sink_map)
            self._available=True
        return self

    def set(self, attr: str, fallback: Any) -> "_LazyModuleProxy":
        """Set a fallback value for ``attr`` when using sink mode."""

        self._sink_map[f"{self._spec.alias}.{attr}"] = fallback
        return self

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
                self._available = True
                return obj
            if self._sink:
                self._obj = _SinkProxy(self._spec.alias, self._sink_map)
                self._available = True
            else:
                self._obj = _MissingPackage(self._spec.alias)
            return self._obj

    def __getattr__(self, item: str) -> Any:
        if self._obj is _UNSET and self._sink:
            return _AttrProxy(self, item)
        return getattr(self._load(), item)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._load()(*args, **kwargs)

    def __bool__(self) -> bool:
        return self.is_available

    def __repr__(self) -> str:  # pragma: no cover - trivial
        state = "loaded" if self._obj is not _UNSET else "pending"
        return f"<lazyshell.Proxy {self._spec.path} ({state})>"

    def __eq__(self, other):
        if other is True or other is False:
            raise TypeError(
                f"Invalid comparison: `{self._spec.alias or self._spec.module}` == {other}.\n"
                "Use `if proxy:` or `if not proxy:` instead of `== True` or `== False`.\n"
                "if a direct comparison is required use proxy.is_available==True"
            )
        return NotImplemented

    def __ne__(self, other):
        if other is True or other is False:
            raise TypeError(
                f"Invalid comparison: `{self._spec.alias or self._spec.module}` != {other}.\n"
                "Use `if proxy:` or `if not proxy:` instead of `!= True` or `!= False`.\n"
                "if a direct comparison is required use proxy.is_available==False"
            )
        return NotImplemented

    @property
    def is_loaded(self) -> bool:
        """Return ``True`` if the underlying object has been imported."""
        return self._obj is not _UNSET

    @property
    def is_available(self) -> bool:
        if self._obj is _UNSET:
            self._load()
        return self._available

ModuleSpec = Union[str, Tuple[str, str]]


def shell_import(
    *modules: ModuleSpec,
    sink: bool = False,
    sink_map: Dict[str, Any] | None = None,
) -> "_LazyModuleProxy" | Tuple["_LazyModuleProxy", ...]:
    """Return proxies for the given modules or objects."""

    proxies = []
    for mod in modules:
        if isinstance(mod, tuple):
            alias, path = mod
        else:
            path = mod
            alias = mod.split(".")[0]
        proxy = _LazyModuleProxy(
            _ImportSpec(alias=alias, path=path), sink=sink, sink_map=sink_map
        )
        proxies.append(proxy)

    if len(proxies) == 1:
        return proxies[0]
    return tuple(proxies)

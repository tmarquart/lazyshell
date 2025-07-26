import importlib
import threading
import pytest

from lazy_shell import shell_import


def test_lazy_import_once(monkeypatch):
    calls = []

    real_import = importlib.import_module

    def mock_import(name, package=None):
        calls.append(name)
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", mock_import)
    (math_proxy,) = shell_import("math")
    assert calls == []
    assert math_proxy.sqrt(4) == 2
    assert calls == ["math"]
    assert math_proxy.sqrt(9) == 3
    assert calls == ["math"]


def test_missing_sink_false():
    (missing,) = shell_import("no_such_package_xyz", sink=False)
    assert not bool(missing)
    with pytest.raises(ImportError):
        missing.foo


def test_missing_sink_true():
    (sink,) = shell_import("no_such_package_xyz", sink=True)
    assert bool(sink)
    assert sink.foo.bar() is None


def test_sink_map_override(capsys):
    (sink,) = shell_import("no_pkg", sink=True, sink_map={"no_pkg.log": print})
    sink.log("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.out


def test_threaded_import(monkeypatch):
    calls = []
    real_import = importlib.import_module

    def mock_import(name, package=None):
        calls.append(name)
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", mock_import)
    (math_proxy,) = shell_import("math")

    def worker():
        assert math_proxy.sqrt(16) == 4

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert calls.count("math") == 1


def test_truthiness_flip():
    (proxy,) = shell_import("math")
    assert not bool(proxy)
    proxy.sqrt(4)
    assert bool(proxy)

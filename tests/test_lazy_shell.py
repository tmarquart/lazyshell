import importlib
import logging
import threading
import pytest

from src.lazyshell import shell_import

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def test_lazy_import_once(monkeypatch):
    logger.info("start lazy_import_once")
    calls = []

    real_import = importlib.import_module

    def mock_import(name, package=None):
        calls.append(name)
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", mock_import)
    (math_proxy,) = shell_import("math")
    logger.info("proxy created")
    assert calls == []
    assert math_proxy.sqrt(4) == 2
    logger.info("first import calls: %s", calls)
    assert calls == ["math"]
    assert math_proxy.sqrt(9) == 3
    logger.info("second call no import")
    assert calls == ["math"]
    logger.info("end lazy_import_once")


def test_missing_sink_false():
    logger.info("start missing_sink_false")
    (missing,) = shell_import("no_such_package_xyz", sink=False)
    assert not bool(missing)
    with pytest.raises(ImportError):
        missing.foo
    logger.info("end missing_sink_false")


def test_missing_sink_true():
    logger.info("start missing_sink_true")
    (sink,) = shell_import("no_such_package_xyz", sink=True)
    assert bool(sink)
    assert sink.foo.bar() is None
    logger.info("end missing_sink_true")


def test_sink_map_override(capsys):
    logger.info("start sink_map_override")
    (sink,) = shell_import("no_pkg", sink=True, sink_map={"no_pkg.log": print})
    sink.log("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.out
    logger.info("end sink_map_override")


def test_threaded_import(monkeypatch):
    logger.info("start threaded_import")
    calls = []
    real_import = importlib.import_module

    def mock_import(name, package=None):
        calls.append(name)
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", mock_import)
    (math_proxy,) = shell_import("math")
    logger.info("proxy created")

    def worker():
        logger.info("worker running")
        assert math_proxy.sqrt(16) == 4

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert calls.count("math") == 1
    logger.info("end threaded_import")


def test_truthiness_flip():
    logger.info("start truthiness_flip")
    (proxy,) = shell_import("math")
    assert not bool(proxy)
    proxy.sqrt(4)
    assert bool(proxy)
    logger.info("end truthiness_flip")


def test_multi_module_submodule(tmp_path, monkeypatch):
    logger.info("start multi_module_submodule")
    import sys

    # create dummy numpy package
    numpy_dir = tmp_path / "numpy"
    numpy_dir.mkdir()
    (numpy_dir / "__init__.py").write_text("def round(x):\n    return int(x)\n")

    # create dummy pandas package
    pandas_dir = tmp_path / "pandas"
    pandas_dir.mkdir()
    (pandas_dir / "__init__.py").write_text("")

    # create dummy jinja2 package with Environment class
    jinja_dir = tmp_path / "jinja2"
    jinja_dir.mkdir()
    (jinja_dir / "__init__.py").write_text(
        "class Environment:\n    def __init__(self, name):\n        self.name = name\n"
    )

    sys.path.insert(0, str(tmp_path))
    logger.info("dummy modules inserted")
    calls = []
    real_import = importlib.import_module

    def mock_import(name, package=None):
        calls.append(name)
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", mock_import)

    np, pd, ne, Env = shell_import(
        "numpy", "pandas", "fake", "jinja2.Environment"
    )
    logger.info("proxies created")

    assert not bool(np)
    assert np.round(3.6) == 3
    assert bool(np)
    assert "numpy" in calls

    env = Env("lulz")
    logger.info("submodule created: %s", env.name)
    assert env.name == "lulz"
    assert any(c.startswith("jinja2") for c in calls)

    assert "pandas" not in calls

    assert not bool(ne)
    with pytest.raises(ImportError):
        ne.foo
    
    sys.path.remove(str(tmp_path))
    for mod in ["numpy", "pandas", "jinja2"]:
        if mod in sys.modules:
            del sys.modules[mod]
    logger.info("end multi_module_submodule")
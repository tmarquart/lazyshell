from src.lazyshell import shell_import
import pytest


def test_single_module():
    math = shell_import("math")
    assert math.sqrt(9) == 3


def test_multiple_modules():
    math, sys_mod, missing = shell_import("math", "sys", "no_such_pkg")
    assert math.factorial(5) == 120
    assert hasattr(sys_mod, "path")
    assert not bool(missing)
    with pytest.raises(ImportError):
        missing.foo


def test_submodule_class():
    Path = shell_import("pathlib.Path")
    p = Path("/tmp")
    assert str(p) == r"\tmp"


def test_sink_proxy():
    missing = shell_import("does.not.exist", sink=True)
    assert bool(missing)
    assert missing.foo.bar() is None

def test_is_loaded_property():
    math = shell_import("math")
    assert not math.is_loaded
    math.sqrt(4)
    assert math.is_loaded


from src.lazyshell import shell_import
import pytest
#import xgboost as xgb

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

def test_lazy():
    xgb = shell_import('xgboost')

    #print(xgb.__version__)

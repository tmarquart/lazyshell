import pytest
from src.lazyshell import shell_import


def test_load_success():
    math = shell_import("math")
    assert not math
    assert not math.is_loaded
    assert math.sqrt(9) == 3
    assert math.is_loaded
    assert math


def test_missing_no_sink():
    missing = shell_import("does.not.exist")
    assert not missing
    with pytest.raises(ImportError):
        missing.foo
    assert missing.is_loaded
    assert not missing


def test_with_sink():
    missing = shell_import("does.not.exist").with_sink()
    assert not missing.is_loaded
    # trigger loading
    assert missing.foo.bar() is None
    assert missing.is_loaded
    assert bool(missing)


def test_set_fallback_via_attr():
    captured = []

    def logger(msg):
        captured.append(msg)

    hass = shell_import("does.not.exist").with_sink()
    hass.log.set(logger)
    hass.log("hi")
    assert captured == ["hi"]


def test_enable_sink_after_failure():
    proxy = shell_import("does.not.exist")
    with pytest.raises(ImportError):
        proxy.foo()
    assert proxy.is_loaded
    proxy.enable_sink()
    assert proxy.foo() is None
    assert bool(proxy)


# content of test_module.py
import pytest

from tox_docker import escape_env_var


@pytest.mark.parametrize(
    "original,expected",
    [("my.private.registry/cat/image", "MY_PRIVATE_REGISTRY_CAT_IMAGE"), ("cat/image", "CAT_IMAGE")],
)
def test_func_fast(original, expected):
    escapedVar = escape_env_var(original)
    assert expected == escapedVar

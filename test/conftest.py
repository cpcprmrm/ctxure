import sys

import pytest

from ctxure import register

if sys.version_info < (3, 12):
    collect_ignore_glob = ["*py312.py"]


@pytest.fixture
def testregister():
    return register.copy()


@pytest.fixture(autouse=True)
def clear_register_cache():
    # Keep tests independent of what earlier tests cached on the global dispatcher.
    # mutmut forks each mutant run from a process that has already run the tests.
    register.structure_cache.clear()
    register.unstructure_cache.clear()

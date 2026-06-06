import sys

import pytest

from ctxure import register

if sys.version_info < (3, 12):
    collect_ignore_glob = ["*py312.py"]


@pytest.fixture
def testregister():
    return register.copy()

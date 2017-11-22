import pytest
import tempfile

@pytest.fixture(scope='function')
def tempdir():
    with tempfile.TemporaryDirectory() as dir:
        yield dir

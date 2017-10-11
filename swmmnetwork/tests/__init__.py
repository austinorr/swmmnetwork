from pkg_resources import resource_filename

import swmmnetwork
from .utils import data_path

try:
    import pytest

    def test(*args):
        options = [resource_filename('swmmnetwork', 'tests')]
        options.extend(list(args))
        return pytest.main(options)

except ImportError:
    def test():
        print("Tests require `pytest`")

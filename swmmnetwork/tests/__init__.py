from pkg_resources import resource_filename

try:
    import pytest

    def test(*args):
        options = [resource_filename('swmmnetwork', 'tests')]
        options.extend(list(args))
        return pytest.main(options)

except ImportError:
    def test(*args):
        print("Tests require `pytest`")

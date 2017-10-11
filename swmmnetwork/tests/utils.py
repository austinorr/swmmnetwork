from pkg_resources import resource_filename

def data_path(filename):
    path = resource_filename("swmmnetwork.tests.data", filename)
    return path
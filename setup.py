#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
import io
import os
from setuptools import setup, find_packages


def get_pkg_info(info_file, info):
    val = ""
    info_file.seek(0)
    for line in info_file:
        if line.startswith('__{}__'.format(info)):
            val = line.split("=")[1].replace("'", "").replace('"', "").strip()
    return val

with open(os.path.join('swmmnetwork', '__init__.py')) as init_file:
    author = get_pkg_info(init_file, 'author')
    email = get_pkg_info(init_file, 'email')
    version = get_pkg_info(init_file, 'version')


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'networkx',
    'pandas',
    'numpy',
    'pint==0.8.1',
]

test_requirements = [
    'pytest',
]

package_data = {
    'swmmnetwork.tests.data': ['*'],
}

setup(
    name='swmmnetwork',
    author=author,
    author_email=email,
    version=version,
    description="SWMMNetwork helps users of EPA SWMM 5.1 perform water quality and load reduction calculations. ",
    long_description=readme + '\n\n' + history,
    url='https://github.com/austinorr/swmmnetwork',
    packages=find_packages(),
    package_data=package_data,
    include_package_data=True,
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords='swmmnetwork',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)

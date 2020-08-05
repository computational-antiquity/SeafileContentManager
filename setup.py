# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    # Application name:
    name="SeafileContentManager",

    # Version number (initial):
    version="0.1.2",

    # Application author details:
    author="Malte Vogl",
    author_email="mvogl@mpiwg-berlin.mpg.de",

    # Packages
    packages=find_packages(exclude=('tests', 'example')),

    # Include additional files into the package
    include_package_data=True,

    url='https://github.com/computational-antiquity/SeafileContentManager/',

    # Details

    license='GPLv3',
    description="ContentManager using Seafile's WebAPI",

    long_description=long_description,
    long_description_content_type='text/markdown',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Text Processing :: General',
        'Topic :: Text Processing :: Indexing',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
    ],

    project_urls={
        'Tracker': 'https://github.com/computational-antiquity/SeafileContentManager/issues',
        'Download': 'https://github.com/computational-antiquity/SeafileContentManager/archive/0.1.1.tar.gz',
    },

    python_requires='>=3',

    # Dependent packages (distributions)
    install_requires=[
        "nbformat",
        "requests"
        ],
    test_suite='nose.collector',
    tests_require=['nose'],
)

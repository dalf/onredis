#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from pathlib import Path

from setuptools import setup


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    version = Path(package, "__version__.py").read_text()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", version).group(1)


def get_long_description():
    """
    Return the README.
    """
    long_description = ""
    with open("README.md", encoding="utf8") as f:
        long_description += f.read()
    return long_description


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [str(path.parent) for path in Path(package).glob("**/__init__.py")]


setup(
    name="onredis",
    python_requires=">=3.7",
    version=get_version("onredis"),
    url="https://github.com/dalf/onredis",
    project_urls={
        "Source": "https://github.com/dalf/onredis",
    },
    license="BSD",
    description="Classes on Redis.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Alexandre Flament",
    author_email="alex.andre@al-f.net",
    packages=get_packages("onredis"),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "redis>=4",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
)

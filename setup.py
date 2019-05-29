#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="scarif",
    description="Open source tape library control",
    author="Thomas Bennett",
    author_email="thomas@ska.ac.za",
    packages=find_packages(),
    install_requires=[
        "serial"
    ],
    url='http://ska.ac.za/',
    # scripts=[
        # "scripts/xxx.py",
    # ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    platforms=["OS Independent"],
    keywords="ska sarao",
    zip_safe=False,
)

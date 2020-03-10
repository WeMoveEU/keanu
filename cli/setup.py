#!/usr/bin/env python
import setuptools

with open("../README.MD", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='keanu-etl',
    version='0.4',
    author="Romain Thouvenin, Marcin Koziej",
    author_email="romain@wemove.eu, marcin@cahoots.pl",
    description="Analytics ETL and collaboration tool for progressive campaigning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.wemove.eu/internal/keanu",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['keanu = keanu.cli:cli']
    },
    use_pipfile=True
 )

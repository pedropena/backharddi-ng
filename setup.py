#!/usr/bin/python
# -*- coding: utf8 -*-

from setuptools import setup, find_packages
setup(name='Backharddi NG',
        version='0.1',
        author=u'Pedro Peña Pérez',
        author_email='pedro.pena@open-phoenix.com',
        license='GPL',
        setup_requires=['nose>=0.10'],
        test_suite="nose.collector",
        packages=find_packages(),
    )

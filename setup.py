#!/usr/bin/env python
from setuptools import setup
import glob

scripts = glob.glob("scripts/*")

setup(name='acispy',
      packages=['acispy'],
      version='0.4.1',
      description='Python tools for ACIS Ops',
      author='John ZuHone',
      author_email='jzuhone@gmail.com',
      url='http://github.com/jzuhone/acispy',
      download_url='https://github.com/jzuhone/acispy/tarball/0.4.0',
      install_requires=["six","requests","astropy"],
      scripts=scripts,
      classifiers=[
          'Intended Audience :: Science/Research',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7'
      ],
      )

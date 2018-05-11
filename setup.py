#!/usr/bin/env python
from setuptools import setup
import glob

scripts = glob.glob("scripts/*")

from acispy import __version__

setup(name='acispy',
      packages=['acispy'],
      version=__version__,
      description='Python tools for ACIS Ops',
      author='John ZuHone',
      author_email='john.zuhone@cfa.harvard.edu',
      url='http://github.com/jzuhone/acispy',
      download_url='https://github.com/jzuhone/acispy/tarball/0.8.2',
      install_requires=["numpy>=1.13.1","six","requests","astropy"],
      scripts=scripts,
      classifiers=[
          'Intended Audience :: Science/Research',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.6'
      ],
      )

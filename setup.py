#!/usr/bin/env python
from setuptools import setup
import glob
import versioneer

scripts = glob.glob("scripts/*")

setup(name='acispy',
      packages=['acispy'],
      description='Python tools for ACIS Ops',
      author='John ZuHone',
      author_email='john.zuhone@cfa.harvard.edu',
      url='http://github.com/jzuhone/acispy',
      install_requires=["numpy>=1.12.1","six","requests","astropy"],
      scripts=scripts,
      classifiers=[
          'Intended Audience :: Science/Research',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.6'
      ],
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      )

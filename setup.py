#!/usr/bin/env python

from distutils.core import setup

from pinder import __version__

setup(
    name='pinder',
    version=__version__,
    description='Python API for Campfire.',
    license='BSD',
    author='Lawrence Oluyede',
    author_email='l.oluyede@gmail.com',
    url='http://dev.oluyede.org/pinder/',
    download_url='http://dev.oluyede.org/download/pinder/0.6.5/',
    packages=['pinder'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Communications :: Chat',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
) 

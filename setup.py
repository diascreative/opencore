# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz.org
#               2010-2011 Large Blue
#               Fergus Doyle: fergus.doyle@largeblue.com
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

__version__ = '0.1dev'

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.txt')).read()
except IOError:
    README = ''

requires = [
    'appendonly',
    'Beaker',
    'deform',
    'feedparser',
    'htmllaundry',
    'lxml',
    'PILwoTk',
    'repoze.bfg >= 1.3',
    'repoze.browserid',
    'repoze.catalog',
    'repoze.errorlog',
    'repoze.evolution',
    'repoze.folder',
    'repoze.lemonade',
    'repoze.retry',
    'repoze.sendmail  >= 2.2',
    'repoze.session',
    'repoze.tm2',
    'repoze.who',
    'repoze.who-friendlyform',
    'repoze.whoplugins.zodb',
    'repoze.workflow',
    'repoze.zodbconn',
    'simplejson',
    'WebError',
    'ZODB3',
    # testing requirements
    'coverage',
    'mock',
    'nose',
    'testfixtures',
    'zope.testing', # fwd compat when not directly relied on by BFG
    ]

setup(name='opencore',
      version=__version__,
      description='OpenCore',
      long_description=README,
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        ],
      keywords='web wsgi zope',
      author="Large Blue",
      author_email="info@largeblue.com",
      url="http://www.largeblue.com/opencore",
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      include_package_data=True,
      zip_safe=False,
      install_requires = requires,
      tests_require = requires,
      test_suite="nose.collector",
      entry_points = """
        [paste.app_factory]
        [paste.filter_app_factory]
        gateway = opencore.middleware.gateway:GatewayMiddleware
        [console_scripts]
        debug = opencore.scripts.debug:main
        reindex_catalog = opencore.scripts.reindex_catalog:main
        rename_user = opencore.scripts.rename_user:main
        site_announce = opencore.scripts.site_announce:main
        mvcontent = opencore.scripts.mvcontent:main
        evolve = opencore.scripts.evolve:main
        make_admin = opencore.scripts.make_admin:main
       
       """
)


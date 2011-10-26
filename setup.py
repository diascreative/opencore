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


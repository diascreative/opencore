__version__ = '0.1dev'

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.txt')).read()
except IOError:
    README = ''

requires = [
    'setuptools',
    'ZODB3',
    'coverage',
    'feedparser',
    'FormEncode',
    'lxml',
    'PILwoTk',
    'nose',
    'repoze.bfg >= 1.3',
    'repoze.browserid',
    'repoze.catalog',
    'repoze.evolution',
    'repoze.folder == 0.4',
    'repoze.lemonade',
    'repoze.monty',
    'repoze.retry',
    'repoze.sendmail',
    'repoze.session',
    'repoze.tm2',
    'repoze.who',
    'repoze.who-friendlyform',
    'repoze.whoplugins.zodb',
    'repoze.zodbconn',
    'zope.testing', # fwd compat when not directly relied on by BFG
    'simplejson',
    'webtest',
    'BeautifulSoup',
    'repoze.errorlog',
    'supervisor',
    'recaptcha-client',
    'bitlyapi',
    'Baker',
    'WebError',
    'appendonly'
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
        [console_scripts]
       
       """
)


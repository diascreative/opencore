from zope.interface import Attribute
from zope.interface import Interface

class IBootstrapper(Interface):
    """ Bootstraps a Karl instance by populating the ZODB with an initialized site
        structure.
    """
    def __call__(root):
        """ Creates a Karl site in the ZODB root with the name 'site'.
        """

class IInitialData(Interface):
    """ Provides data used to initialize a Karl site.

        TODO: Extend interface to require attributes referenced in
              opencore.bootstrap.bootstrap.populate
    """

class IInitialOfficeData(Interface):
    """ Provides data used to initialize offices.
    """

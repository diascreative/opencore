from zope.interface import Interface
from zope.interface import Attribute

class IAtomFeed(Interface):
    """ Flatten contents into data for an Atom feed """

    id = Attribute('The atom:id of the feed')
    title = Attribute('The atom:title of the feed')
    subtitle = Attribute('The atom:subtitle of the feed')
    link = Attribute('The atom:link of the feed')
    entries = Attribute('The sequence of feed entries')

class IAtomEntry(Interface):
    """ Specification for a single entry in an atom feed.
    """
    title = Attribute("Entry Title")
    uri = Attribute("URI of resource represented by this atom entry.")
    published = Attribute("Date initially published."+
                          "(instance of datetime.datetime)")
    updated = Attribute("Date last modified." +
                        "(instance of datetime.datetime)")
    author = Attribute("Author information in a dict with two entries: " +
                       "'name', the author's name, and 'uri', which is the " +
                       "uri of the author's profile page in Karl.")
    content = Attribute("Html content of entry.")

class ISidebar(Interface):
    """Renders an HTML sidebar.

    Sidebars are registered as multi-adapters of (model, request), similar to
    views.
    """
    def __call__(api):
        """Render the sidebar.

        api is an instance of TemplateAPI.
        """

class IFolderAddables(Interface):
    """ Policies for what can be added to a container """

    def __call__():
        """Return a sequence of what can be added"""

class IToolAddables(Interface):
    """ Policies for what tools can be added to a community """

    def __call__():
        """Return a sequence of what can be added"""

class ILayoutProvider(Interface):
    """ Policy to get the o-wrap in a certain context"""

    def __call__():
        """ Make this adapter be simply a callable """


class IInvitationBoilerplate(Interface):
    """Gets membership terms/conditions and privacy statement"""
    terms_and_conditions = Attribute('Terms and conditions as HTML')
    privacy_statement = Attribute('Privacy statement as HTML')


class IFooter(Interface):
    """Renders an HTML footer.

    o Registered as a multi-adapters of (model, request).
    """
    def __call__(api):
        """Render the footer.

        o api is an instance of TemplateAPI.
        """

class IIntranetPortlet(Interface):
    """ Adaptation of various data sources into a portlet """
    title = Attribute('The title of the portlet')
    href = Attribute('URL to get to the container being summarized')
    entries = Attribute('Up to five of the entries')

class IFileInfo(Interface):
    """ An interface representing file info for display in views """
    name = Attribute('The name of the file in its container')
    title = Attribute('The title of the file or folder')
    modified = Attribute('A string representing the modification time/date '
                         'of the file or folder')
    url = Attribute('A url for the file or folder')
    mimeinfo = Attribute('Mime information for the file or folder '
        '(instance of karl.utilities.interfaces.IMimeInfo)')
    size = Attribute('File size with units such as MB')

class IBylineInfo(Interface):
    """ Grabe resource info for showing a byline in ZPT macro"""

    author_name = Attribute('The title of the profile for the creator')
    author_url = Attribute('The URL to the profile of the creator')
    posted_date = Attribute('A pretty representation of the posted date')

class IFolderCustomizer(Interface):
    """ Use adaptation to push policies on folder creation out of core"""

    markers = Attribute('Sequence of interfaces to mark the new folder')

class IShowSendalert(Interface):
    """ Policy for when to show-hide the sendalert choice """
    
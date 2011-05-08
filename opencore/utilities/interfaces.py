from zope.interface import Attribute
from zope.interface import Interface

class IMimeInfo(Interface):
    """ Utility for getting mimeinfo such as icon filename
    """
    def __call__(mimetype):
        """ Return a dictionary in the form

        {'small_icon_name':<relative_filename>, 'title':<title>}

        to service mimetype graphical information """


class IMailinTextScrubber(Interface):
    """ Utility for cleaning text of mail-in content.
    """
    def __call__(text, mimetype=None, is_reply=False):
        """ Return scrubbed version of 'text'.

        o 'mimetype', if passed, will be the MIME type of the part from
          which 'text' was extracted.

        o If 'is_reply' is True, extra processing may be done to attempt to
          separate the reply from the replied to message.
        """
        
class ICatalogSearchArgs(Interface):
    """ Utility to add extra args to a catalog search.
    """
    def __call__(args):
        """ Given args transform and return as kw args suitable 
        for extending an existing catalog search"""

class IAppDates(Interface):
    """ Utility for various representations of a date
    """
    def __call__(date, flavor):
        """ Given DateTime, return string formmated in various flavors """

class IRandomId(Interface):
    """ A utility which returns a random identifier string """
    def __call__(size=6):
        """ Return the ranomly generated string of ``size`` characters"""

class ISpellChecker(Interface):
    """ A utility that provides a wrapper for interacting with an
        external Aspell spell checker subprocess. """

#XXX Does this go here?
class IAlert(Interface):
    """An alert message, suitable for emailing or digesting."""

    mfrom = Attribute("Email address of sender.")
    mto = Attribute("Sequence of email addresses for all recipients.")
    message = Attribute("An instance of repoze.postoffice.message.Message "
                        "to be mailed.")
    digest = Attribute("""Boolean, can be set by caller to indicate alert
                       should be formatted for digest.""")

class IAlerts(Interface):
    """A utility which emits activity alerts to community members.
    """
    def emit(context, factory, request):
        """Emits an alert.

        For each user to be alerted will either send the alert immediately,
        add to a digest queue, or not send at all, according to member
        preferences.

          o context is place in model tree in which alert is occuring.
          o factory is a callable which can generate an IAlert instance and
            has the signature: (context, profile) where context is the same
            object as above and profile is the user being alerted.
        """

    def send_digests(context):
        """Iterates over all user profiles and sends digested alerts.  Will
        generally be called by a console script which in turn is called by
        cron.

        o context can be an model object in the site hierarchy, usually the
          root.

        """

class IMessenger(Interface):
     
    def send(mfrom, profile, message):
        """Sends an alert message to a users inbox.
        """           
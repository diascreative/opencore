from BTrees.IFBTree import multiunion
from BTrees.IFBTree import IFSet

from repoze.bfg.security import Allow
from repoze.bfg.security import Deny
from repoze.bfg.security import Everyone
from repoze.bfg.security import AllPermissionsList
from repoze.bfg.traversal import model_path
from repoze.who.plugins.zodb.users import Users
import logging

log = logging.getLogger(__name__)

VIEW = 'view'
EDIT = 'edit'
CREATE = 'create'
DELETE = 'delete'
DELETE_COMMUNITY = 'delete community'
MODERATE = 'moderate'
ADMINISTER = 'administer'
COMMENT = 'comment'

GUEST_PERMS = (VIEW, COMMENT)
MEMBER_PERMS = GUEST_PERMS + (EDIT, CREATE, DELETE)
MODERATOR_PERMS = MEMBER_PERMS + (MODERATE,)
ADMINISTRATOR_PERMS = MODERATOR_PERMS + (ADMINISTER, DELETE_COMMUNITY)

ALL = AllPermissionsList()
NO_INHERIT = (Deny, Everyone, ALL)

class ACLChecker(object):
    """ 'Checker' object used as a ``attr_checker`` callback for a
        path index set up to use the __acl__ attribute as an
        ``attr_discriminator``
    """
    def __init__(self, principals, permission='view'):
        self.principals = principals
        self.permission = permission

    def __call__(self, result):
        sets = []
        for (docid, acls), set in result:
            if not set:
                continue
            if self.check_acls(acls):
                sets.append(set)
        if not sets:
            return IFSet()
        return multiunion(sets)

    def check_acls(self, acls):
        acls = list(reversed(acls))
        for acl in acls:
            for ace in acl:
                ace_action, ace_principal, ace_permissions = ace
                if ace_principal in self.principals:
                    if not hasattr(ace_permissions, '__iter__'):
                        ace_permissions = [ace_permissions]
                    if self.permission in ace_permissions:
                        if ace_action == Allow:
                            return True
                        else:
                            # deny of any means deny all of everything
                            return False
        return False

def get_groups(identity, request):
    if 'groups' in identity:
        return identity['groups']

def ace_repr(ace):
    action = ace[0]
    principal = ace[1]
    permissions = ace[2]
    if not hasattr(permissions, '__iter__'):
        permissions = [permissions]
    if permissions == ALL:
        permissions = ['ALL']
    permissions = sorted(list(set(permissions)))
    return '%s %s %s' % (action, principal, ', '.join(permissions))

def acl_diff(ob, acl):
    ob_acl = getattr(ob, '__acl__', {})
    if ob_acl != acl:
        added = []
        removed = []
        for ob_ace in ob_acl:
            if ob_ace not in acl:
                removed.append(ace_repr(ob_ace))
        for ace in acl:
            if ace not in ob_acl:
                added.append(ace_repr(ace))
        return '|'.join(added), '|'.join(removed)
    return None, None

def find_users(root):
    # Called by repoze.who
    # XXX Should this really go here?
    zodb_root = 'site'
    if not zodb_root in root:
        return Users()
    return root[zodb_root].users  

def to_profile_active(ob):
    from opencore.utils import find_users
    from opencore.views.communities import get_community_groups
    acl  = [
        (Allow, ob.creator, MEMBER_PERMS + ('view_only',)),
    ]
    acl.append((Allow, 'group.KarlUserAdmin',
                ADMINISTRATOR_PERMS + ('view_only',)))
    acl.append((Allow, 'group.KarlAdmin',
                ADMINISTRATOR_PERMS + ('view_only',)))
    acl.append((Allow, 'group.KarlStaff',
                GUEST_PERMS + ('view_only',)))
    users = find_users(ob)
    user = users.get_by_id(ob.creator)
    if user is not None:
        groups = user['groups']
        for group, role in get_community_groups(groups):
            c_group = 'group.community:%s:%s' % (group, role)
            acl.append((Allow, c_group, GUEST_PERMS + ('view_only',)))
    acl.append((Allow, 'system.Authenticated', ('view_only',)))
    acl.append(NO_INHERIT)
    added, removed = acl_diff(ob, acl)
    if added or removed:
        ob.__acl__ = acl
        log.info('profile (%s) to-active, added: %s, removed: %s' % (model_path(ob), added, removed))
    #_reindex(ob)
    #_reindex_peopledir(ob)


def to_profile_inactive(ob):
    acl  = [
        (Allow, 'system.Authenticated', ('view_only',)),
        (Allow, 'group.KarlUserAdmin', ADMINISTRATOR_PERMS + ('view_only',)),
        (Allow, 'group.KarlAdmin', ADMINISTRATOR_PERMS + ('view_only',)),
        NO_INHERIT,
    ]
    msg = None
    added, removed = acl_diff(ob, acl)
    if added or removed:
        ob.__acl__ = acl
        log.info('profile (%s) to-inactive, added: %s, removed: %s' % (model_path(ob), added, removed))
    #_reindex(ob)
    #_reindex_peopledir(ob)
  


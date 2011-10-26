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

import unittest

from repoze.bfg import testing

class Test_edit_acl_view(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, context, request):
        from opencore.views.acl import edit_acl_view
        return edit_acl_view(context, request)

    def _makeACL(self, admins=(), moderators=(), members=(), guests=(),
                 no_inherit=True):
        from repoze.bfg.security import Allow
        from opencore.security.policy import ADMINISTRATOR_PERMS
        from opencore.security.policy import GUEST_PERMS
        from opencore.security.policy import MEMBER_PERMS
        from opencore.security.policy import MODERATOR_PERMS
        from opencore.security.policy import NO_INHERIT
        acl = []
        for admin in admins:
            acl.append((Allow, admin, ADMINISTRATOR_PERMS))
        for moderator in moderators:
            acl.append((Allow, moderator, MODERATOR_PERMS))
        for member in members:
            acl.append((Allow, member, MEMBER_PERMS))
        for guest in guests:
            acl.append((Allow, guest, GUEST_PERMS))
        if no_inherit:
            acl.append(NO_INHERIT)
        return acl

    def test_not_submitted_no_local_acl_no_parent(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')

        self._callFUT(context, request)

        self.assertEqual(renderer.parent_acl, ())
        self.assertEqual(renderer.local_acl, [])
        self.assertEqual(renderer.inheriting, 'enabled')

    def test_not_submitted_w_local_acl_no_parent_no_inherit(self):
        context = testing.DummyModel()
        context.__acl__ = self._makeACL(members=('bharney',))
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')

        self._callFUT(context, request)

        self.assertEqual(renderer.parent_acl, ())
        self.assertEqual(renderer.local_acl, context.__acl__[:-1])
        self.assertEqual(renderer.inheriting, 'disabled')

    def test_not_submitted_no_local_acl_w_parent_no_parent_acl(self):
        parent = testing.DummyModel()
        context = parent['child'] = testing.DummyModel()
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')

        self._callFUT(context, request)

        self.assertEqual(renderer.parent_acl, ())
        self.assertEqual(renderer.local_acl, [])
        self.assertEqual(renderer.inheriting, 'enabled')

    def test_not_submitted_w_local_acl_w_inherit_w_parent_w_parent_acl(self):
        parent = testing.DummyModel()
        parent.__acl__ = self._makeACL(admins=('phred',))
        context = parent['child'] = testing.DummyModel()
        context.__acl__ = self._makeACL(guests=('bharney',), no_inherit=False)
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')

        self._callFUT(context, request)

        from opencore.security.policy import NO_INHERIT
        parent_acl = [ace for ace in parent.__acl__ if ace != NO_INHERIT]
        self.assertEqual(renderer.parent_acl, parent_acl)
        self.assertEqual(renderer.local_acl, context.__acl__)
        self.assertEqual(renderer.inheriting, 'enabled')

    def test_not_submitted_no_local_acl_w_parent_w_parent_acl(self):
        parent = testing.DummyModel()
        parent.__acl__ = self._makeACL(admins=('phred',))
        context = parent['child'] = testing.DummyModel()
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')

        self._callFUT(context, request)

        from opencore.security.policy import NO_INHERIT
        parent_acl = [ace for ace in parent.__acl__ if ace != NO_INHERIT]
        self.assertEqual(renderer.parent_acl, parent_acl)
        self.assertEqual(renderer.local_acl, [])
        self.assertEqual(renderer.inheriting, 'enabled')

    def test_not_submitted_no_local_acl_w_grand_w_grand_acl(self):
        grand = testing.DummyModel()
        grand.__acl__ = self._makeACL(admins=('phred',))
        parent = grand['child'] = testing.DummyModel()
        context = parent['grandchild'] = testing.DummyModel()
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')

        self._callFUT(context, request)

        from opencore.security.policy import NO_INHERIT
        grand_acl = [ace for ace in grand.__acl__ if ace != NO_INHERIT]
        self.assertEqual(renderer.parent_acl, grand_acl)
        self.assertEqual(renderer.local_acl, [])
        self.assertEqual(renderer.inheriting, 'enabled')

    def test_not_submitted_no_local_acl_w_grand_w_inherited_acl(self):
        grand = testing.DummyModel()
        grand.__acl__ = self._makeACL(admins=('phred',))
        parent = grand['child'] = testing.DummyModel()
        parent.__acl__ = self._makeACL(members=('bharney',), no_inherit=False)
        context = parent['grandchild'] = testing.DummyModel()
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')

        self._callFUT(context, request)

        from opencore.security.policy import NO_INHERIT
        grand_acl = [ace for ace in grand.__acl__ if ace != NO_INHERIT]
        self.assertEqual(renderer.parent_acl, parent.__acl__ + grand_acl)
        self.assertEqual(renderer.local_acl, [])
        self.assertEqual(renderer.inheriting, 'enabled')

    def test_submitted_move_up_at_top_unchanged_no_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.move_up'] = '^'
        request.POST['index'] = 0

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl)

    def test_submitted_move_up_not_at_top_moves_up_no_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.move_up'] = '^'
        request.POST['index'] = 1

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl[1:2] + acl[0:1] + acl[2:])

    def test_submitted_move_up_at_top_unchanged_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.move_up'] = '^'
        request.POST['index'] = 0

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl)

    def test_submitted_move_up_not_at_top_moves_up_inherit(self):
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.move_up'] = '^'
        request.POST['index'] = 1

        testing.registerDummyRenderer('karl.views:templates/edit_acl.pt')
        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl[1:2] + acl[0:1] + acl[2:])

    def test_submitted_move_down_at_bottom_unchanged_no_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.move_down'] = 'v'
        request.POST['index'] = 1

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl)

    def test_submitted_move_down_not_at_bottom_moves_down_no_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.move_down'] = 'v'
        request.POST['index'] = 0

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl[1:2] + acl[0:1] + acl[2:])

    def test_submitted_move_down_at_bottom_unchanged_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.move_down'] = 'v'
        request.POST['index'] = 1

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl)

    def test_submitted_move_down_not_at_bottom_moves_down_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.move_down'] = 'v'
        request.POST['index'] = 0

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl[1:2] + acl[0:1] + acl[2:])

    def test_submitted_remove_no_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.remove'] = 'X'
        request.POST['index'] = 0

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl[1:])

    def test_submitted_remove_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.remove'] = 'X'
        request.POST['index'] = 1

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl[:1])

    def test_submitted_add_no_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.add'] = 'Add'
        request.POST['verb'] = 'Allow'
        request.POST['principal'] = 'wylma'
        request.POST['permissions'] = 'view'

        self._callFUT(context, request)

        self.assertEqual(context.__acl__,
                         acl[:-1] + [('Allow', 'wylma', ('view',))] + acl[-1:])

    def test_submitted_add_inherit(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.add'] = 'X'
        request.POST['verb'] = 'Allow'
        request.POST['principal'] = 'wylma'
        request.POST['permissions'] = 'view'

        self._callFUT(context, request)

        self.assertEqual(context.__acl__,
                         acl + [('Allow', 'wylma', ('view',))])

    def test_submitted_add_mulitple_permissions(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.add'] = 'X'
        request.POST['verb'] = 'Allow'
        request.POST['principal'] = 'wylma'
        request.POST['permissions'] = 'view, comment'

        self._callFUT(context, request)

        self.assertEqual(context.__acl__,
                         acl + [('Allow', 'wylma', ('view', 'comment'))])

    def test_submitted_inherit_enabled_inherited(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.inherit'] = 'Update Inherited'
        request.POST['inherit'] = 'enabled'

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl)

    def test_submitted_inherit_enabled_not_inherited(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.inherit'] = 'Update Inherited'
        request.POST['inherit'] = 'enabled'

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl[:-1])

    def test_submitted_inherit_disabled_inherited(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        from opencore.security.policy import NO_INHERIT
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                              no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.inherit'] = 'Update Inherited'
        request.POST['inherit'] = 'disabled'

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl + [NO_INHERIT])

    def test_submitted_inherit_disabled_not_inherited(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        acl = context.__acl__ = self._makeACL(admins=('phred', 'bharney'))
        request = testing.DummyRequest()
        request.POST['form.inherit'] = 'Update Inherited'
        request.POST['inherit'] = 'disabled'

        self._callFUT(context, request)

        self.assertEqual(context.__acl__, acl)

    def test_submitted_at_root_reindexes_acl(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        context.docid = 1
        catalog = context.catalog = DummyCatalog()
        index = catalog['allowed'] = DummyIndex()
        context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                        no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.add'] = 'X'
        request.POST['verb'] = 'Allow'
        request.POST['principal'] = 'wylma'
        request.POST['permissions'] = 'view'

        self._callFUT(context, request)

        self.assertEqual(index._reindexed, (1, context))
        self.failUnless(catalog._invalidated)

    def test_submitted_not_at_root_reindexes_acl(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        parent = testing.DummyModel()
        context = parent['child'] = testing.DummyModel()
        context.docid = 1
        catalog = parent.catalog = DummyCatalog()
        index = catalog['allowed'] = DummyIndex()
        context.__acl__ = self._makeACL(admins=('phred', 'bharney'),
                                        no_inherit=False)
        request = testing.DummyRequest()
        request.POST['form.add'] = 'X'
        request.POST['verb'] = 'Allow'
        request.POST['principal'] = 'wylma'
        request.POST['permissions'] = 'view'

        self._callFUT(context, request)

        self.assertEqual(index._reindexed, (1, context))
        self.failUnless(catalog._invalidated)
   
    def test_submitted_reindexes_children(self):
        testing.registerDummyRenderer('templates/edit_acl.pt')
        context = testing.DummyModel()
        context.docid = 1
        child = context['child'] = testing.DummyModel()
        child.docid = 2
        catalog = context.catalog = DummyCatalog()
        index = catalog['allowed'] = DummyIndex()
        context.__acl__ = []
        request = testing.DummyRequest()
        request.POST['form.add'] = 'X'
        request.POST['verb'] = 'Allow'
        request.POST['principal'] = 'wylma'
        request.POST['permissions'] = 'view'

        self._callFUT(context, request)

        self.assertEqual(index._reindexed, (1, context), (2, child))
        self.failUnless(catalog._invalidated)

    def test_show_no_workflow(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        renderer = testing.registerDummyRenderer('templates/edit_acl.pt')
        self._callFUT(context, request)
        self.assertEqual(renderer.security_state, None)
        self.assertEqual(renderer.security_states, None)

   
class Test_acl_tree_view(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, context, request):
        from opencore.views.acl import acl_tree_view
        return acl_tree_view(context, request)

    def test_it(self):
        class DummyModel(testing.DummyModel):
            def _p_deactivate(self):
                self.deactivated = True
        from repoze.folder.interfaces import IFolder
        from zope.interface import directlyProvides
        request = testing.DummyRequest()
        context2 = DummyModel()
        context2.__acl__ = ['Allow', 'fred', ('read',)]
        context = DummyModel()
        context['context2'] = context2
        directlyProvides(context, IFolder)
        renderer = testing.registerDummyRenderer('templates/acl_tree.pt')
        self._callFUT(context, request)
        self.assertEqual(len(renderer.acls), 2)
        context_acl = renderer.acls[0]
        self.assertEqual(context_acl,
                         {'path': '/',
                          'acl': None,
                          'name': '/',
                          'offset': 0,
                          'url':'http://example.com/',
                          })
        context2_acl = renderer.acls[1]
        self.assertEqual(context2_acl,
                         {'path': '/context2',
                          'acl': ['Allow', 'fred', ('read',)],
                          'name': 'context2',
                          'offset': 1,
                          'url':'http://example.com/context2/',
                          })
        self.assertEqual(context.deactivated, True)
        self.assertEqual(context2.deactivated, True)

class DummyCatalog(dict):
    _invalidated = False

    def invalidate(self):
        self._invalidated = True

class DummyIndex:
    _reindexed = None
    def reindex_doc(self, docid, object):
        self._reindexed = (docid, object)

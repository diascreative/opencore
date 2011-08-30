import random

from BTrees import IOBTree
from BTrees import OOBTree
from persistent import Persistent
from zope.component import queryAdapter
from zope.event import notify
from zope.interface import implements
from repoze.bfg.traversal import find_model

from opencore.utils import find_catalog
from opencore.utils import find_community
from opencore.tagging.interfaces import ITag
from opencore.tagging.interfaces import ITagAddedEvent
from opencore.tagging.interfaces import ITagCommunityFinder
from opencore.tagging.interfaces import ITaggingEngine
from opencore.tagging.interfaces import ITaggingStatistics
from opencore.tagging.interfaces import ITagRemovedEvent


class _TagEventBase(Persistent):

    def __init__(self, tag):
        self._tag = tag

    item = property(lambda x: x._tag.item,)
    name = property(lambda x: x._tag.name,)
    user = property(lambda x: x._tag.user,)
    community = property(lambda x: x._tag.community,)

    def __cmp__(self, other):
        return cmp(self._tag, other._tag)

    def __hash__(self):
        return hash(self._tag)

    def __repr__(self):
        return '<%s %r >' %(self.__class__.__name__, self._tag)

class TagAddedEvent(_TagEventBase):
    implements(ITagAddedEvent)


class TagRemovedEvent(_TagEventBase):
    implements(ITagRemovedEvent)


class Tag(Persistent):
    """ Simple implementation of a tag.
    """
    implements(ITag)
    _id = None

    def __init__(self, item, user, name, community=None):
        self.item = item
        if not isinstance(user, unicode):
            user = unicode(user, 'utf-8')
        if not isinstance(name, unicode):
            name = unicode(name, 'utf-8')
        self.user = user
        self.name = name
        if community and not isinstance(community, unicode):
            community = unicode(community, 'utf-8')
        self.community = community

    def _clone(self):
        return self.__class__(self.item, self.user, self.name, self.community)

    def __cmp__(self, other):
        return cmp((self.item, self.user, self.name, self.community),
                   (other.item, other.user, other.name, other.community))

    def __hash__(self):
        return (hash(self.item) +
                hash(self.user) +
                hash(self.name) +
                hash(self.community))

    def __repr__(self):
        return '<%s %r for %i by %r, community %r>' %(
            self.__class__.__name__,
            self.name,
            self.item,
            self.user,
            self.community)


class Tags(Persistent):
    implements(ITaggingEngine, ITaggingStatistics)

    _v_nextid = None

    def __init__(self, site):
        self.site = site # need a backref
        self._reset()

    # ITaggingStatistics attributes
    def __len__(self):
        return len(self._tagid_to_obj)

    @property
    def tagCount(self):
        return len(self._name_to_tagids)

    @property
    def itemCount(self):
        return len(self._item_to_tagids)

    @property
    def userCount(self):
        return len(self._user_to_tagids)

    # ITaggingEngine methods.
    def getTagsWithPrefix(self, prefix):
        """ See ITaggingEngine.
        """
        for key in self._name_to_tagids.keys(min=prefix):
            if key.startswith(prefix):
                yield key
            else:
                raise StopIteration

    def getTags(self, items=None, users=None, community=None):
        """ See ITaggingEngine.
        """
        if items is None and users is None and community is None:
            # shortcut
            return set(self._name_to_tagids.keys())

        result = self.getTagObjects(items, users, community=community)
        return set([tag.name for tag in result])

    def getTagObjects(self, items=None, users=None, tags=None, community=None):
        """ See ITaggingEngine.
        """
        ids = self._getTagIds(items, users, tags, community)
        return set([self._tagid_to_obj[id] for id in ids])

    def getCloud(self, items=None, users=None, community=None):
        """ See ITaggingEngine.
        """
        if isinstance(items, int):
            items = [items]
        if isinstance(users, basestring):
            users = [users]

        tags = self.getTagObjects(items=items, users=users,
                                  community=community)
        d = {}
        for tag in tags:
            if d.has_key(tag.name):
                d[tag.name] += 1
            else:
                d[tag.name] = 1
        return set(d.items())

    def getItems(self, tags=None, users=None, community=None):
        """ See ITaggingEngine.
        """
        uids = self._getTagIds(items=None, users=users, tags=tags,
                               community=community)
        res = set()
        for uid in uids:
            o = self._tagid_to_obj.get(uid)
            if o is not None:
                res.add(o.item)
        return res

    def getUsers(self, tags=None, items=None, community=None):
        """ See ITaggingEngine.
        """
        ids = self._getTagIds(items=items, users=None, tags=tags,
                              community=community)
        return set([self._tagid_to_obj[id].user for id in ids])

    def getRelatedTags(self, tag, degree=1, community=None, user=None):
        """ See ITaggingEngine.
        """
        result = set()
        degree_counter = 1
        previous_degree_tags = set([tag])
        degree_tags = set()
        while degree_counter <= degree:
            for cur_name in previous_degree_tags:
                tagids = self._name_to_tagids.get(cur_name, ())
                for tagid in tagids:
                    tag_obj = self._tagid_to_obj[tagid]
                    if community and tag_obj.community != community:
                        continue
                    if user and tag_obj.user != user:
                        continue
                    degree_tags.update(self.getTags(
                                                items=(tag_obj.item,),
                                                users=(tag_obj.user,),
                                                community=community,
                                                ))
            # After all the related tags of this degree were found, update the
            # result set and clean up the variables for the next round.
            result.update(degree_tags)
            previous_degree_tags = degree_tags
            degree_tags = set()
            degree_counter += 1
        # Make sure the original is not included
        if tag in result:
            result.remove(tag)
        return result

    def getRelatedItems(self, item, community=None, user=None):
        """ See ITaggingEngine.
        """
        if user is None:
            tags = self.getTags([item], community=community)
            items = self.getItems(tags, community=community)
        else:
            tags = self.getTags([item], community=community, users=(user,))
            items = self.getItems(tags, community=community, users=(user,))
        if item in items:
            items.remove(item)
        result = []
        for otherItem in items:
            otherTags = self.getTags([otherItem], community=community)
            result.append((otherItem, len(tags.intersection(otherTags))))
        return sorted(result, key=lambda i: i[1], reverse=True)

    def getRelatedUsers(self, user, community=None):
        """ See ITaggingEngine.
        """
        tags = self.getTags(users=[user], community=community)
        users = self.getUsers(tags, community=community)
        if user in users:
            users.remove(user)
        result = []
        for otherUser in users:
            otherTags = self.getTags(users=[otherUser], community=community)
            result.append((otherUser, len(tags.intersection(otherTags))))
        return sorted(result, key=lambda i: i[1], reverse=True)

    def getFrequency(self, tags=None, community=None, user=None):
        """ See ITaggingEngine.
        """
        if user is not None:
            users = [user]
        else:
            users = None
        if tags is None:
            result = {}
        else:
            result = dict((x, 0) for x in tags)
        for tag_id in self._getTagIds(users=users,
                                      tags=tags,
                                      community=community):
            tag_obj = self._tagid_to_obj[tag_id]
            result[tag_obj.name] = result.setdefault(tag_obj.name, 0) + 1
        return sorted(result.items(), key=lambda x: x[1])

    def update(self, item, user, tags):
        """ See ITaggingEngine.
        """
        c_finder = queryAdapter(self, ITagCommunityFinder)
        community = c_finder and c_finder(item) or None

        tags_item = set(self._item_to_tagids.get(item, ()))
        tags_user = set(self._user_to_tagids.get(user, ()))
        tags_user_item = tags_item.intersection(tags_user)

        old_tags = set([self._tagid_to_obj[id] for id in tags_user_item])

        new_tags = set([Tag(item, user, tagName, community)
                            for tagName in tags])

        add_tags = new_tags.difference(old_tags)
        remove_tags = old_tags.difference(new_tags)

        for tagObj in add_tags:
            id = self._add(tagObj)

            ids = self._user_to_tagids.get(user)
            if ids is None:
                self._user_to_tagids[user] = IOBTree.IOSet((id,))
            else:
                ids.insert(id)

            ids = self._item_to_tagids.get(item)
            if ids is None:
                self._item_to_tagids[item] = IOBTree.IOSet((id,))
            else:
                ids.insert(id)

            ids = self._name_to_tagids.get(tagObj.name)
            if ids is None:
                self._name_to_tagids[tagObj.name] = IOBTree.IOSet((id,))
            else:
                ids.insert(id)

            ids = self._community_to_tagids.get(tagObj.community)
            if ids is None:
                self._community_to_tagids[tagObj.community] = \
                    IOBTree.IOSet((id,))
            else:
                ids.insert(id)

            notify(TagAddedEvent(tagObj))

        del_tag_ids = [x._id for x in remove_tags]
        self._delTags(del_tag_ids)

    def delete(self, item=None, user=None, tag=None):
        if item is None and user is None and tag is None:
            raise ValueError('Must specify at least one criterion')
        tags = None
        if item is not None:
            tags = set(self._item_to_tagids.get(item, ()))
        if user is not None:
            user_tags = set(self._user_to_tagids.get(user, ()))
            if tags is not None:
                tags = tags.intersection(user_tags)
            else:
                tags = user_tags
        if tag is not None:
            name_tags = set(self._name_to_tagids.get(tag, ()))
            if tags is not None:
                tags = tags.intersection(name_tags)
            else:
                tags = name_tags
        self._delTags(tags)
        return len(tags)

    def rename(self, old, new):
        """ See ITaggingEngine.
        """
        if old == new:
            return 0
        if not isinstance(new, unicode):
            new = new.decode('utf-8')
        tagIds = set(self._name_to_tagids.get(old, ()))
        for tagId in tagIds:
            tagObj = self._tagid_to_obj[tagId]
            notify(TagRemovedEvent(tagObj._clone()))
            tagObj.name = new
            notify(TagAddedEvent(tagObj))
        newTagIds = IOBTree.IOSet(self._name_to_tagids.get(new, ()))
        newTagIds.update(tagIds)
        self._name_to_tagids[new] = newTagIds
        if tagIds:
            del self._name_to_tagids[old]
        return len(tagIds)

    def reassign(self, olduser, newuser):
        """ See ITaggingEngine.
        """
        old_ids = self._user_to_tagids[olduser]
        if newuser in self._user_to_tagids:
            # XXX This potentially leaves dupes in the tree.
            self._user_to_tagids[newuser].update(old_ids)
        else:
            self._user_to_tagids[newuser] = old_ids
        del self._user_to_tagids[olduser]
        for tagid in old_ids:
            tagobj = self._tagid_to_obj[tagid]
            notify(TagRemovedEvent(tagobj._clone()))
            tagobj.user = unicode(newuser)
            # XXX Ideally, we would filter events for already-existing
            #     identical tags by the new user.
            notify(TagAddedEvent(tagobj))

    def normalize(self, normalizer=None):
        """ See ITaggingEngine.
        """
        if normalizer is None:
            normalizer = lambda x: x.lower()
        names = list(self._name_to_tagids.keys())
        count = 0
        for name in names:
            newName = normalizer(name)
            if newName != name:
                count += self.rename(name, newName)
        return count

    def _reset(self):
        # Map tagid to tag object
        self._tagid_to_obj = IOBTree.IOBTree()

        # Indexes
        self._user_to_tagids = OOBTree.OOBTree()
        self._item_to_tagids = IOBTree.IOBTree()
        self._name_to_tagids = OOBTree.OOBTree()
        self._community_to_tagids = OOBTree.OOBTree()

    def _generateId(self):
        """Generate an id which is not yet taken.

        This tries to allocate sequential ids so they fall into the
        same BTree bucket, and randomizes if it stumbles upon a
        used one.
        """
        while True:
            if self._v_nextid is None:
                self._v_nextid = random.randrange(0, 2**31)
            uid = self._v_nextid
            self._v_nextid += 1
            if uid not in self._tagid_to_obj:
                return uid
            #self._v_nextid = None

    def _add(self, tagObj):
        uid = self._generateId()
        self._tagid_to_obj[uid] = tagObj
        tagObj._id = uid
        return uid

    def _getTagIds(self, items=None, users=None, tags=None, community=None):
        if (items is None and users is None and
            tags is None and community is None):
            # get them all
            result = set()
            for v in self._item_to_tagids.values():
                result.update(v)
        else:
            if community is not None:
                communities = [community]
            else:
                communities = None
            result = None
            for seq, bt in ((items, self._item_to_tagids),
                            (users, self._user_to_tagids),
                            (tags, self._name_to_tagids),
                            (communities, self._community_to_tagids)):
                res = set()
                if seq is not None:
                    for item in seq:
                        res.update(bt.get(item, set()))
                    if result is not None:
                        result = result.intersection(res)
                    else:
                        result = res
        return result

    def _delTags(self, del_tag_ids):
        """deletes tags in iterable"""
        for id in del_tag_ids:
            tagObj = self._tagid_to_obj[id]
            self._user_to_tagids[tagObj.user].remove(id)
            if not len(self._user_to_tagids[tagObj.user]):
                del self._user_to_tagids[tagObj.user]

            self._item_to_tagids[tagObj.item].remove(id)
            if not len(self._item_to_tagids[tagObj.item]):
                del self._item_to_tagids[tagObj.item]

            self._name_to_tagids[tagObj.name].remove(id)
            if not len(self._name_to_tagids[tagObj.name]):
                del self._name_to_tagids[tagObj.name]

            self._community_to_tagids[tagObj.community].remove(id)
            if not len(self._community_to_tagids[tagObj.community]):
                del self._community_to_tagids[tagObj.community]

            del self._tagid_to_obj[id]
            notify(TagRemovedEvent(tagObj))

class TopicFilteredTags(Tags):
     
    def getTags(self, items=None, users=None, community=None):
        """ See ITaggingEngine.
        """
        if items is None and users is None and community is None:
            # shortcut
            return set([x for x in self._name_to_tagids.keys() 
                       if not x.startswith('topic.')]) 
    
        result = self.getTagObjects(items, users, community=community)
        return set([tag.name for tag in result])  # self.getTagObjects() deals with filtering
    
    def getTagObjects(self, items=None, users=None, tags=None, community=None):
        """ See ITaggingEngine.
        """
        ids = self._getTagIds(items, users, tags, community)
        objs = [self._tagid_to_obj[id] for id in ids]
        return set([obj for obj in objs if not obj.name.startswith('topic.')])
    
    def getFrequency(self, tags=None, community=None, user=None):
        """ See ITaggingEngine.
        """
        if user is not None:
            users = [user]
        else:
            users = None
        if tags is None:
            result = {}
        else:
            result = dict((x, 0) for x in tags)
        for tag_id in self._getTagIds(users=users,
                                      tags=tags,
                                      community=community):
            tag_obj = self._tagid_to_obj[tag_id]
            if not tag_obj.name.startswith('topic.'):
                result[tag_obj.name] = result.setdefault(tag_obj.name, 0) + 1
        return sorted(result.items(), key=lambda x: x[1])
    
    def getTopics(self, items=None, users=None, community=None, strip_prefix=False):
        """ See ITaggingEngine.
        """
        if items is None and users is None and community is None:
            # shortcut
            return set([x for x in self._name_to_tagids.keys() 
                       if x.startswith('topic.')]) 
    
        result = self.getTopicObjects(items, users, community=community)
        if strip_prefix:
            return set([tag.name.replace('topic.', '', 1) for tag in result]) # self.getTopicObjects() deals with filtering
        else:
            return set([tag.name for tag in result]) # self.getTopicObjects() deals with filtering
    
    def getTopicObjects(self, items=None, users=None, tags=None, community=None):
        """ See ITaggingEngine.
        """
        ids = self._getTagIds(items, users, tags, community)
        objs = [self._tagid_to_obj[id] for id in ids]
        return set([obj for obj in objs if obj.name.startswith('topic.')])
         
class TagCommunityFinder(object):
    implements(ITagCommunityFinder)

    def __init__(self, context):
        self.context = context

    def __call__(self, docid):
        site = self.context.site
        catalog = find_catalog(site)
        if catalog is None:
            raise ValueError('No catalog')
        path = catalog.document_map.address_for_docid(docid)
        if path is None:
            raise KeyError(docid)
        doc = find_model(site, path)
        community = find_community(doc)
        return community and community.__name__ or None

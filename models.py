from google.appengine.ext import ndb
from google.appengine.api import memcache
import hashlib
import datetime
import logging

class RentRecord(ndb.Model):
    last_update = ndb.DateTimeProperty(auto_now=True)
    title       = ndb.StringProperty()
    url         = ndb.StringProperty(indexed=False)
    text        = ndb.StringProperty(indexed=False)
    address     = ndb.StringProperty(repeated=True)
    telephone   = ndb.StringProperty(repeated=True)
    location    = ndb.GeoPtProperty(repeated=True)
    pics        = ndb.StringProperty(repeated=True)
    room_type   = ndb.StringProperty(repeated=True)
    price       = ndb.IntegerProperty(repeated=True)

    @classmethod
    def __get_ndb_key(cls, key):
        """returns ndb_key if not existing"""
        record_key = ndb.Key(cls, key)
        if record_key.get():
            return None
        return record_key

    @classmethod
    def get_key(cls, data):
        try:
            title   = data['title']
            text    = data['text']
        except:
            return None

        key = hashlib.sha256(title.encode('utf-8') + text.encode('utf-8')).hexdigest()
        return ndb.Key(cls, key)

    @classmethod
    def add_record(cls, data):
        try:
            title   = data['title']
            text    = data['text']
        except:
            return False

        key = hashlib.sha256(title.encode('utf-8') + text.encode('utf-8')).hexdigest()

        ndb_key = cls.__get_ndb_key(key)
        if not ndb_key: return False

        valid_properties = {}
        for cls_prop in cls._properties:
            if cls_prop in data:
                if cls_prop == 'location':
                    valid_properties.update({cls_prop: [ndb.GeoPt(i['lat'], i['lng']) for i in data[cls_prop]]})
                elif cls_prop == 'last_update':
                    logging.debug(data[cls_prop])
                else:
                    valid_properties.update({cls_prop: data[cls_prop]})

        valid_properties['key'] = ndb_key

        try:
            entity = cls(**valid_properties).put()
        except Exception as e:
            logging.error(repr(e))
            return False

        return entity

def fetch_query(query, prefix):
    for key in query.fetch(keys_only=True):
        cache_key = prefix % key.urlsafe()
        data = memcache.get(cache_key)
        if not data:
            data = key.get().to_dict()
            memcache.set(cache_key, data)
        yield data


class User(ndb.Model):
    fake_id = ndb.StringProperty()
    reminder_sent = ndb.BooleanProperty(default=False)
    last_active = ndb.DateTimeProperty(auto_now_add=True)
    items       = ndb.KeyProperty(kind=RentRecord, repeated=True)
    item_hits   = ndb.StringProperty(repeated=True)

    cache_key_prefix = 'user_%s'

    @classmethod
    def add_user(cls, fake_id):
        key = ndb.Key(cls, fake_id)
        user = key.get()
        if user: return fake_id

        try:
            logging.debug('new user!')
            User(key=key, fake_id=fake_id).put()
        except Exception as e:
            logging.error(repr(e))
            return False
        return fake_id

    @classmethod
    def touch_user(cls, fake_id):
        key = ndb.Key(cls, fake_id)
        user = key.get()
        try:
            user.last_active = datetime.datetime.utcnow()
            user.reminder_sent = False
            user.put()
        except Exception as e:
            logging.error(repr(e))
            return False
        return True

    @classmethod
    def mark_user(cls, fake_id):
        key = ndb.Key(cls, fake_id)
        user = key.get()
        try:
            user.reminder_sent = True
            user.put()
        except Exception as e:
            logging.error(repr(e))
            return False
        return True

    @classmethod
    def get_user(cls, fake_id):
        if memcache.get(cls.cache_key_prefix % fake_id):
            return memcache.get(cls.cache_key_prefix % fake_id)

        key = ndb.Key(cls, fake_id)
        user = key.get()
        data = user.to_dict()

        if not user: return None
        memcache.set(cls.cache_key_prefix % fake_id, data)
        return data

    @classmethod
    def update_user_items(cls, fake_id, items):
        key = ndb.Key(cls, fake_id)
        if not key: return False

        try:
            user = key.get()
            prev_items = user.items
            prev_hits  = user.item_hits

            new_items = [RentRecord.get_key(item) for item in items]
            new_hits  = [item['hit'] for item in items]

            prev_items.extend(new_items)
            prev_hits.extend(new_hits)

            user.items = prev_items[-20:]
            user.item_hits = prev_hits[-20:]
            user.put()

            data = user.to_dict()
            memcache.set(cls.cache_key_prefix % fake_id, data)
        except Exception as e:
            logging.error(repr(e))
            return False
        return data


class Subscription(ndb.Model):
    keyword = ndb.StringProperty()
    fake_id = ndb.StringProperty()

    cache_key_prefix = 'subscription_%s'

    @classmethod
    def add_subscription(cls, fake_id, keyword):
        User.add_user(fake_id)
        key = ndb.Key(cls, keyword+fake_id)
        subscription = key.get()
        if subscription: return subscription
        try:
            ret = cls(key=key, keyword=keyword, fake_id=fake_id).put()
        except Exception as e:
            logging.error(repr(e))
            return False

        return ret

    @classmethod
    def remove_subscription(cls, fake_id, keyword):
        key = ndb.Key(cls, keyword+fake_id)

        try:
            memcache.delete(cls.cache_key_prefix % key.urlsafe)
            ret = key.delete()
        except Exception as e:
            logging.error(repr(e))
            return False

        return True

    @classmethod
    def get_user_subscriptions(cls, fake_id):
        q = cls.query(cls.fake_id == fake_id)
        result = [i for i in fetch_query(q, cls.cache_key_prefix)]
        return sorted(result, key=lambda x: x['keyword'])

    @classmethod
    def get_active_subscriptions(cls):
        deadline = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        users = [u['fake_id'] for u in fetch_query(User.query(User.last_active > deadline), User.cache_key_prefix)]
        if not len(users):
            return []

        q = cls.query(cls.fake_id.IN(users))
        result = [i for i in fetch_query(q, cls.cache_key_prefix)]
        return result


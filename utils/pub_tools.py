from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.api import memcache

import re
import json
import logging
import urllib

from models import User, RentRecord
from templates import JINJA_ENVIRONMENT

from wechat_config import conf
import site_config
import api_config

def filter_items(items, subscriptions):
    result = {}
    for item in items:
        for sub in subscriptions:
            regexp = re.compile(sub['keyword'])
            user = sub['fake_id']
            if regexp.search(item['title']) \
                    or regexp.search(item['text']) \
                    or regexp.search(' '.join(item['address'])):
                item['hit'] = sub['keyword']
                if user in result:
                    result[user].append(item)
                else:
                    result[user] = [item]
    return result

def render_user_items(user):
    user_data = User.get_user(user)

    items = ndb.get_multi(user_data['items'])
    template = JINJA_ENVIRONMENT.get_template('templates/items.html')

    context = {
            'items': [i.to_dict() if i else {} for i in items]
            }
    result = template.render(context)
    return result

def get_short_url(user):
    short_url = 'https://api-ssl.bitly.com/v3/shorten?access_token=%s&longUrl=%s&domain=bitly.com' % (api_config.bitly_token,
            urllib.quote(site_config.url + '?user=%s' % user))
    cache_key = 'short_url_%s' % user

    url = memcache.get(cache_key)
    if not url:
        ret = urlfetch.fetch(url=short_url)
        response = json.loads(ret.content)
        if response['data']:
            url = response['data']['url']
            memcache.set(cache_key, url)
        else:
            logging.error(str(response))
            return
        logging.debug('user %s shorturl: %s' % (user, url))
    return url




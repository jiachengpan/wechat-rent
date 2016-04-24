from wechat_web import Wechat
import wechat_config
import logging

from google.appengine.api import memcache

cache_key = 'WECHAT_SESSION'

client = memcache.get(cache_key)
if not client:
    try:
        client = Wechat(wechat_config.account_name, wechat_config.account_passwd)
        client.login()
        client.get_fakeid()
        client.get_available_users()
        memcache.set(cache_key, client)
    except Exception as e:
        logging.error(repr(e))

def send_message(fake_id, message):
    try:
        client.send_message(fake_id, message)
    except Exception as e:
        logging.error(repr(e))
        return False
    return True



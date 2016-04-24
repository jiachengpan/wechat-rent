# coding: utf-8
import webapp2

from google.appengine.api import taskqueue
from google.appengine.api import runtime

import logging
import os
import time
import re
import datetime

import json
import wechat_sdk
import wechat_config

from models import Subscription, RentRecord, User
from utils.rent_parser import RentParser
from utils.pub_tools import filter_items, render_user_items, get_short_url

from wechat_sdk import WechatBasic
from wechat_sdk import messages
wechat = WechatBasic(conf = wechat_config.conf)

import messenger
import site_config

root_dir = os.path.dirname(os.path.abspath(__file__))


class MainHandler(webapp2.RequestHandler):
    def get(self):
        signature = self.request.get('signature')
        timestamp = self.request.get('timestamp')
        nonce     = self.request.get('nonce')
        echostr   = self.request.get('echostr')
        if wechat.check_signature(signature, timestamp, nonce):
            self.response.write(echostr)
        else:
            self.response.write('')

    def post(self):
        USAGE = u"""使用方法：
* 回复 "1 <关键字>", 接收租房推送；
* 回复 "2"， 查询当前订阅的关键字；
* 回复 "3 <编号>"， 取消查询结果中编号对应的关键字；
* 回复任意信息，续定推送（微信有规定48小时内没交流就不许我发信息给你了。。。）
"""

        signature = self.request.get('msg_signature')
        timestamp = self.request.get('timestamp')
        nonce     = self.request.get('nonce')
        try:
            wechat.parse_data(self.request.body, signature, timestamp, nonce)
            if isinstance(wechat.message, messages.TextMessage):
                content = wechat.message.content.strip()
                user = wechat.message.source
                resp = ''
                logging.debug('got message (%s) from %s' % (content, user))
                try:
                    if re.match(u'1', content):
                        keyword = content[1:].strip()
                        ret = Subscription.add_subscription(user, keyword)
                        logging.debug(ret)
                        if ret:
                            resp = u'订阅成功！'
                        else:
                            raise Exception('subscription failed')
                    elif re.match(u'3', content):
                        try:
                            idx = int(content[1:].strip())
                            ret = Subscription.get_user_subscriptions(user)
                            if len(ret):
                                if idx < len(ret):
                                    keyword = ret[idx]['keyword']
                                    ret = Subscription.remove_subscription(user, keyword)
                                    if ret:
                                        resp = u'订阅取消成功（%s）！' % keyword
                                    else:
                                        raise Exception('subscription removal failed')

                                else:
                                    resp = u'没有找到编号为%d的订阅诶。。您一共有%d个订阅。' % (idx, len(ret))
                            else:
                                resp = u'您当前没有订阅。'
                        except Exception as e:
                            raise
                    elif re.match(u'2', content):
                        ret = Subscription.get_user_subscriptions(user)
                        if len(ret):
                            resp = u'您的当前订阅：\n%s' % '\n'.join(
                                    ['%d: %s' % (idx, r['keyword']) for idx, r in enumerate(ret)])
                        else:
                            resp = u'您当前没有订阅。'
                    else:
                        # TODO: respond something meaningful
                        resp = USAGE

                except Exception as e:
                    logging.debug(repr(e))
                    resp = USAGE

                logging.debug('replying with (%s)' % resp)
                self.response.write(wechat.response_text(resp))

        except Exception as e:
            logging.warning(repr(e))
            logging.warning(e.message)
            import traceback
            traceback.print_exc()
            self.response.write('')

class MenuSetHandler(webapp2.RequestHandler):
    def get(self):
        import yaml
        try:
            with open(os.path.join(root_dir, 'menu_config.yaml')) as fh:
                menu_data = yaml.load(fh)
                logging.debug(menu_data)
                wechat.create_menu(menu_data)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('success')
        except wechat_sdk.exceptions.OfficialAPIError as e:
            logging.warning(repr(e))
            logging.warning(e.message)
            logging.warning(e.errmsg)
            self.response.write('')
        except Exception as e:
            logging.warning(repr(e))
            logging.warning(e.message)
            self.response.write('')


class DataPostHandler(webapp2.RequestHandler):
    def post(self):
        taskqueue.add(url='/_processing/parse_and_pub', params={'items': self.request.body})

class DataParseAndPubHandler(webapp2.RequestHandler):
#    def remind(self, active_subs):
#        REMINER_MSG = """Hi!! 您的订阅即将过期（距上次收到您的信息已接近48小时）。如想继续接收推送，请回复任意信息。谢谢！
#        您当前订阅的关键字如下：
#        %s"""
#
#        deadline = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
#
#        users = {}
#        ok_users = set()
#        for sub in active_subs:
#            user = sub['fake_id']
#            if not sub['reminder_sent'] and sub['last_active'] < deadline:
#                if user in users:
#                    users[user].append(sub['keyword'])
#                else:
#                    users[user] = [sub['keyword']]
#            else:
#                ok_users.add(user)
#
#        for user, kw in users.items():
#            if user in ok_users: continue
#            for k in kw:
#                Subscription.mark_subscription(user, k)
#            logging.debug('sending reminder to %s' % user)
#            messenger.send_message(user, REMINER_MSG % '\n'.join(kw))

    def post(self):
        active_subs = Subscription.get_active_subscriptions()

        items = json.loads(self.request.get('items'))
        logging.debug('before parsing, memory: %s' % runtime.memory_usage().current())
        parser = RentParser()
        parsed_items = []

        for item in items:
            try:
                parsed  = parser.parse(item)
                ret     = RentRecord.add_record(parsed)
            except Exception as e:
                logging.error(repr(e))

            parsed_items.append(parsed)

        logging.debug('after parsing, memory: %s' % runtime.memory_usage().current())

        user2message = filter_items(parsed_items, active_subs)

        for user, item in user2message.items():
            logging.debug('user: %s has %d messages' % (user, len(item)))
            User.update_user_items(user, item)
            url = get_short_url(user)
            if not url:
                url = site_config.url + '?user=%s' % user
            msg = [u'新找到%d条租房信息。' % len(item),
                   u'点击以下链接查看：',
                   url]

            messenger.send_message(user, '\n'.join(msg))

class ViewHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.get('user')
        if not user: return

        self.response.write(render_user_items(user))

class TestAddSubHandler(webapp2.RequestHandler):
    def get(self):
        user    = self.request.get('user')
        keyword = self.request.get('keyword')

        Subscription.add_subscription(user, keyword)

class TestWechatMessengerHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write(messenger.client.get_fakeid())


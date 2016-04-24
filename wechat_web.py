import requests
import hashlib
import re
import time
import logging
import pickle
import os
import json

class Wechat(object):
    headers = {
        "Host": "mp.weixin.qq.com",
        "Origin": "https://mp.weixin.qq.com/",
        "Referer": "https://mp.weixin.qq.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
        "Cookie": "noticeLoginFlag=1",
        "Connection": "keep-alive",
    }

    def __init__(self, user, passwd):
        self.user   = user
        self.passwd = passwd
        self.token  = ''
        self.fakeid = ''

        self.available_users = {}
        self.available_users_id = set()
        self.session = requests.Session()
        self.loggedin= False

    def login(self):
        if self.loggedin: return True
        if not self.token:
            logging.info('logging in')

            URL = "https://mp.weixin.qq.com/cgi-bin/login"
            token_regexp = re.compile('token=(\d+)')
            payload = {
                    'username': self.user,
                    "pwd": hashlib.md5(self.passwd).hexdigest(),
                    'imgcode': '',
                    'f': 'json',
                    }
            response = self.session.post(URL, data=payload, headers=Wechat.headers)

            ret = token_regexp.findall(response.content)
            if not ret:
                logging.error('token fetch failed')
                logging.error(response.content)
                return False
            self.token = ret[0]
        else:
            URL = "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token=%s" % self.token
            response = self.session.get(URL)
            if response.status_code != 200:
                logging.error('login failed with token %s' % self.token)
                return False
        self.loggedin = True
        return True

    def get_fakeid(self):
        '''get fakeid of yourself'''
        if not self.login(): return

        URL = "https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&action=index&token=%s&lang=zh_CN" % self.token
        fakeid_regexp = re.compile('fakeid=(\d{10})')


        response = self.session.get(URL)
        ret = fakeid_regexp.findall(response.content)
        if not ret:
            logging.error('failed to get fakeid')
            return
        self.fakeid = ret[0]
        return self.fakeid

    def get_users(self):
        if not self.login(): return

        URL = "https://mp.weixin.qq.com/cgi-bin/contactmanage?t=user/index&pageidx=0&type=0&token=%s&lang=zh_CN" % self.token
        URL_USER = "https://mp.weixin.qq.com/cgi-bin/contactmanage?t=user/index&pageidx=%s&type=0&token=%s&lang=zh_CN"

        user_count_regexp = re.compile("totalCount : '(\d*)'")
        page_count_regexp = re.compile("pageCount : '(\d*)'")
        page_size_regexp  = re.compile("pageSize : '(\d*),'")
        user_ids_regexp   = re.compile('"id":"(.*?){28}"')
        user_names_regexp = re.compile('"nick_name":"(.*?)"')

        response = self.session.get(URL)
        try:
            user_count = int(user_count_regexp.findall(response.content)[0])
            page_count = int(page_count_regexp.findall(response.content)[0])
            page_size  = int(page_size_regexp.findall(response.content)[0])
        except Exception as e:
            logging.error('failed to get user count / page count / page size')
            logging.error(str(e))
            return

        user_ids = []
        user_names = []
        for idx in range(page_count):
            response = self.session.get(URL_USER % (str(idx), self.token))

            user_ids.extend(user_ids_regexp.findall(response.content))
            user_names.extend(user_names_regexp.findall(response.content))
        self.users = dict(zip(user_names, user_ids))
        return self.users

    def get_available_users(self):
        '''get users whom you can send messages to'''
        if not self.login(): return

        URL = "https://mp.weixin.qq.com/cgi-bin/message?t=message/list&action=&keyword=&offset=0&count=%d&day=7&filterivrmsg=&token=%s&lang=zh_CN"

        total_count_regexp  = re.compile('total_count : (\d*)')
        user_fakeids_regexp = re.compile('"fakeid":"(.*?){28}"')
        user_names_regexp   = re.compile('"nick_name":"(.*?)"')
        date_time_regexp    = re.compile('"date_time":(\d*)')

        now = time.time()

        response = self.session.get(URL % (20, self.token))
        try:
            total_count = int(total_count_regexp.findall(response.content)[0])
        except Exception as e:
            logging.error('failed to get total user count')
            logging.error(str(e))
            return

        response = self.session.get(URL % (total_count, self.token))

        user_fakeids = user_fakeids_regexp.findall(response.content)
        user_names   = user_names_regexp.findall(response.content)
        date_time    = map(int, date_time_regexp.findall(response.content))

        available_user_count = len([i for i in date_time if (now-i) < 172800])

        self.available_users = dict(zip(
            user_names[:available_user_count],
            user_fakeids[:available_user_count]))
        self.available_users_id = set(user_fakeids[:available_user_count])

        return self.available_users

    def send_message(self, to, message):
        if not self.login(): return

        if to not in self.available_users and to not in self.available_users_id:
            self.get_available_users()
            if to not in self.available_users and to not in self.available_users_id:
                logging.error('user %s is not in the latest available user list' % to)
                return False

        if to in self.available_users:
            to_id = self.available_users[to]
        else:
            to_id = to

        URL = "https://mp.weixin.qq.com/cgi-bin/singlesend?t=ajax-response&f=json&token=%s&lang=zh_CN" % self.token

        headers = {
            "Host": "mp.weixin.qq.com",
            "Origin": "https://mp.weixin.qq.com",
            "Referer": "https://mp.weixin.qq.com/cgi-bin/singlesendpage?t=message/send&action=index&tofakeid=%s&token=%s&lang=zh_CN" % (to_id, self.token),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"
        }
        payload = {
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
            "random": "0.4469808244612068",
            "type": "1",
            "content": message,
            "tofakeid": to_id,
            "imgcode": ''
        }

        response = self.session.post(URL, data=payload, headers=headers)
        if response.status_code == 200:
            ret = json.loads(response.content)
            error_msg = ret['base_resp']['err_msg']
            if error_msg == 'ok':
                logging.info('message sent to %s' % to)
                return True
            else:
                logging.error(error_msg)
                return False
        return False


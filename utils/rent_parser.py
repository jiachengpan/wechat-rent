# coding: utf-8
import logging
import os
import re
import tempfile
import sys
import urllib
import api_config
import json

from google.appengine.api import urlfetch

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

import jieba
# we cannot use tempfile in appengine, so cache files are generated in advance locally
jieba.dt.tmp_dir = os.path.join(root_dir, 'resources/cache/')
jieba.default_logger.removeHandler(jieba.log_console)
jieba.dt.cache_file = os.path.join(root_dir, 'resources/cache/jieba.cache')
jieba.dt.load_userdict(os.path.join(root_dir, 'resources/dict/shanghai.dict'))

import jieba.posseg


zh_num = u'一两三四五六七八九二'
num2zh_num = { str(i+1): zh_num[i] for i in range(9) }


class RentParser(object):
    regexp_room_type = re.compile(
            u'(([0-9%s][居房室厅卫]+)+)' % zh_num,
            re.UNICODE)
    regexp_price = re.compile(
            u'(\d{3,5})([元]?[/每]?月|元)|(价格|租金|价)\D?(\d{3,5})\D',
            re.UNICODE)
    regexp_tele= re.compile(
            u'(1\d{2}-?\d{3}-?\d{5}|1\d{2}-?\d{4}-?\d{4})',
            re.UNICODE)

    def query_place(self, text):
        URL = 'https://maps.googleapis.com/maps/api/place/textsearch/json?'

        form_fields = {
                'query': text.encode('utf-8'),
                'key': api_config.api_key,
                'language': 'zh_cn',
                }
        form_data = urllib.urlencode(form_fields)
        try:
            response = urlfetch.fetch(
                    url=URL + form_data,
                    deadline=60,
                    )
        except Exception as e:
            logging.error(str(e))
            return

        data = json.loads(response.content)
        if data['status'] != 'OK':
            logging.warning('Status isnt ok: %s' % data['status'])
            if 'error_message' in data:
                logging.warning('Error: %s' % data['error_message'])
            return

        result = []
        for item in data['results']:
            result.append(item['geometry']['location'])
        return result

    """simple text parser, refer to zhaoxinwo/zufang"""
    def parse_room_type(self, text):
        result = set()
        for match in self.regexp_room_type.findall(text):
            match = ''.join([num2zh_num[c] if c in num2zh_num else c for c in match[0]])
            result.add(match.replace(u'二', u'两'))
        return list(result)

    def parse_price(self, text):
        result = set()
        for match in self.regexp_price.findall(text):
            result.add(int(match[0] if match[0] else int(match[-1])))
        return list(result)

    def parse_address(self, text):
        result = set()
        for seg in jieba.posseg.cut(text):
            if seg.flag in ('shanghai',):
                result.add(seg.word)
        return list(result)

    def parse_telephone(self, text):
        result = set()
        for match in self.regexp_tele.findall(text):
            result.add(match.replace('-', ''))
        return list(result)


    def parse_text(self, text):
        room_type   = self.parse_room_type(text)
        price       = self.parse_price(text)
        address     = self.parse_address(text)
        telephone   = self.parse_telephone(text)

        #if len(address):
        if False:
            location = self.query_place(u'上海' + ' '.join(address))
        else:
            location = []
        return {
                u'room_type':    room_type,
                u'price':        price,
                u'address':      address,
                u'telephone':    telephone,
                u'location':     location,
                }

    def parse(self, data):
        '''fed with {'title': ..., 'text': ..., ...}, ...'''

        try:
            more_context = self.parse_text('%s,%s' % (data['title'], data['text']))
            data.update(more_context)
            return data
        except Exception as e:
            logging.error(e)
            logging.error(e.message)
            raise


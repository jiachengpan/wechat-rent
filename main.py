import webapp2
import sys

import handlers

app = webapp2.WSGIApplication([
    ('/',               handlers.ViewHandler),
    ('/_wechat/',       handlers.MainHandler),
    ('/_static/menu',   handlers.MenuSetHandler),
    ('/_comm/data',         handlers.DataPostHandler),
    ('/_processing/parse_and_pub',  handlers.DataParseAndPubHandler),
    ('/_test/subscription', handlers.TestAddSubHandler),
    ('/_test/wechat',       handlers.TestWechatMessengerHandler),
], debug=True)

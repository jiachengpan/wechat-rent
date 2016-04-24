wechat-rent
===========

Wechat-rent is a pet project for subscribing interested keywords and locations (wip) and publishing qualified renting information (crawled from [douban](www.douban.com)) to wechat users who subscribe the wechat public account (订阅号).

Credits go to:
* [douban](www.douban.com) for the information
* [wechat-sdk](https://github.com/wechat-python-sdk/wechat-python-sdk) for the python wechat sdk
* [jieba](https://github.com/fxsjy/jieba) for tokenising and parsing
* [google app engine](https://appengine.google.com/) for the platform (of course...)
* [material design lite](https://getmdl.io/) for the frontend template
* [bitly](https://bitly.com) for the shorturl conversion

It is essentially a "frontend" specialised in:
* parsing renting information and extracing address, telephone, price, geolocation (w.i.p.), etc.
* managing per-user subscriptions
* publishing renting information to user as per their interests
* hosting user items

It is backed by the [gae-cralwer project](https://github.com/jiachengpan/gae-crawler).

[A sample page storing renting information that interests me...](https://bitly.com/1SrwvQq)

WIP. I myself is currently testing with a not-yet-public "wechat public account"(订阅号) and benefiting from it :smirk:

Cheers, <br>
Jiacheng

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import feedparser
import datetime
from django.utils import simplejson
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class FeedTagCloudCache(db.Model):
  url = db.StringProperty(required=True)
  json = db.TextProperty()
  last_modified = db.DateTimeProperty(auto_now=True)

class FeedTagCloudJsonHandler(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/javascript; charset=utf-8'

    feed_url = self.request.get('url', default_value='')
    if not feed_url:
      logging.error('No URL defined')
      self.error(500)
      return

    cache = None
    try:
      cache = FeedTagCloudCache.gql('WHERE url = :url ORDER BY last_modified DESC', url=feed_url).get()
      if cache:
        expires = cache.last_modified + datetime.timedelta(hours=1)
        if expires > datetime.datetime.now():
          logging.info('Succeeded to get a feed cache: %s' % feed_url)

          self.response.headers.add_header('Expires', expires.strftime('%d %b %Y %H:%M:%S GMT'))
          self.response.out.write(cache.json)
          return
    except Exception, e:
      logging.error(e)
      pass

    json_text = ''
    if cache:
      json_text = cache.json

    try:
      feed = feedparser.parse(feed_url)
      if feed.bozo:
        raise Exception, 'Failed to fetch feed: %s' % feed_url
      logging.info('Succeeded to parse feed: %s' % feed_url)

      tag_cloud = {}
      for entry in feed.entries:
        if not 'tags' in entry:
          continue
        for tag in entry.tags:
          tag_name = tag.term
          if tag_name in tag_cloud:
            tag_cloud[tag_name] += 1
          else:
            tag_cloud[tag_name] = 1
      json_text = simplejson.dumps(tag_cloud, ensure_ascii=False)
    except Exception, e:
      logging.error(e)
      logging.info('Failed to parse feed: %s' % feed_url)
      pass

    if not json_text:
      logging.error('No json text defined: %s' % feed_url)
      self.error(500)
      return

    try:
      if cache:
        cache.json = json_text
        cache.put()
        logging.info('Succeeded to update a feed cache: %s' % feed_url)
      else:
        cache = FeedTagCloudCache(url=feed_url, json=json_text)
        cache.put()
        logging.info('Succeeded to create a feed cache: %s' % feed_url)

      expires = cache.last_modified + datetime.timedelta(hours=1)
      self.response.headers.add_header('Expires', expires.strftime('%d %b %Y %H:%M:%S GMT'))
      self.response.out.write(json_text)
      return
    except Exception, e:
      logging.error(e)
      logging.info('Failed to put a feed cache: %s' % feed_url)
      self.error(500)

class FeedTagCloudHandler(webapp.RequestHandler):
  content = ''
  params = {
    'default_feed_url': 'http://blog.as-is.net/feeds/posts/default?orderby=published&amp;max-results=50&amp;redirect=false',
    'default_base_url': 'http://blog.as-is.net/search/label/'
    }
  def get(self):
    if not self.__class__.content:
      path_url = self.request.path_url
      if path_url[-1] != '/':
        path_url += '/'
      self.params['locale_url'] = path_url + 'locale'
      self.params['json_url'] = path_url + 'json'
      path = os.path.join(os.path.dirname(__file__), 'feed_tagcloud.xml')
      self.__class__.content = template.render(path, self.params)
    else:
      logging.info('Succeeded to reuse template cache')
    self.response.headers['Content-Type'] = 'text/xml; charset=utf-8'
    self.response.out.write(self.__class__.content)

def main():
  application = webapp.WSGIApplication([
      ('/', FeedTagCloudHandler),
      ('/json', FeedTagCloudJsonHandler),
      ], debug=False)
  run_wsgi_app(application)

if __name__ == '__main__':
  main()

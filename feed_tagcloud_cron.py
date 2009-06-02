#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import datetime
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class FeedTagCloudCache(db.Model):
  url = db.StringProperty(required=True)
  json = db.TextProperty()
  last_modified = db.DateTimeProperty(auto_now=True)

class FeedTagCloudCacheCleaner(webapp.RequestHandler):
  def get(self):
    expired = datetime.datetime.now() - datetime.timedelta(days=7)
    query = FeedTagCloudCache.gql("WHERE last_modified < :expired", expired=expired)
    for cache in query:
      cache.delete()

def main():
  application = webapp.WSGIApplication([
      ('/cron', FeedTagCloudCacheCleaner),
      ], debug=False)
  run_wsgi_app(application)

if __name__ == '__main__':
  main()

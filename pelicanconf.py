#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals
from datetime import date

AUTHOR = 'Bernd Viefhues'
SITENAME = 'Hotelfloors'
SITESUBTITLE = "Corridors, Hallways and Staircases"
SITEURL = 'https://hotelfloors.net'

PATH = 'content'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'en'
DEFAULT_DATE = 'fs'

THEME = 'theme/gallery'
DIRECT_TEMPLATES = ['index']
MENUITEMS = [('About', '/pages/about.html'), ('Contact', '/pages/contact.html')]
STATIC_PATHS = ['favicon/favicon.ico', 'favicon/apple-touch-icon.png']
EXTRA_PATH_METADATA = {
    'favicon/favicon.ico': {'path': 'favicon.ico'},
    'favicon/apple-touch-icon.png': {'path': 'apple-touch-icon.png'}
}
CURRENTYEAR = date.today().year

PLUGIN_PATHS = ['../pelican-plugins', 'plugins']
PLUGINS = ['exif_reader', 'sitemap']

SITEMAP = {
    "format": "xml",
    "priorities": {
        "articles": 0.5,
        "indexes": 0.5,
        "pages": 0.5
    },
    "changefreqs": {
        "articles": "monthly",
        "indexes": "daily",
        "pages": "monthly"
    }
}

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

DEFAULT_PAGINATION = 6

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

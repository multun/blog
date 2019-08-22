#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

LOCALE = 'en_US.utf8'

AUTHOR = 'multun'
SITENAME = "Pancakes and computers"
SITEURL = ''

THEME = 'my-theme'

PATH = 'content'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         ('Jinja2', 'http://jinja.pocoo.org/'),
         ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('You can add links in your config file', '#'),
          ('Another social link', '#'),)

DEFAULT_PAGINATION = False
JINJA_ENVIRONMENT = {
    "extensions": ['jinja2.ext.i18n', 'jinja2.ext.do',
                   'jinja2htmlcompress.SelectiveHTMLCompress'],
}

def extract_trans(article, lang, url):
    translations = getattr(article, "translations", [])
    print('found', translations)
    for trans in translations:
        if trans.lang == lang:
            return trans.url
    return url

JINJA_FILTERS = {
    "extract_trans": extract_trans,
}

ARTICLE_TRANSLATION_ID = ["trans_id"]
PAGE_TRANSLATION_ID = ["trans_id"]

# I18N_GETTEXT_LOCALEDIR = 'translations'
# I18N_GETTEXT_DOMAIN = 'messages'

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
PLUGINS = ["i18n_subsites", "simple_footnotes"]
PLUGIN_PATHS = ['plugins']
I18N_SUBSITES = {
        'fr': {
            'SITENAME': 'Crêpes et informatique',
            'LOCALE': 'fr_FR.utf8',
        },
        # 'en': {
        #     'SITENAME': 'english site',
        #     'LOCALE': 'en_US',            #This is somewhat redundant with DATE_FORMATS, but IMHO more convenient
        #     'SITEURL': '../', # silly hack
        # },
}

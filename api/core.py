# -*- coding: utf-8 -*-
"""JIMAM: API system routines"""
from __future__ import print_function
import datetime
import re
import requests
import sys
from settings import *


__author__ = 'https://github.com/fractalvision/'
# Modified by https://github.com/brettwooldridge

try:
   os.makedirs(os.path.join(BASEDIR, 'log'))
except OSError:
   if not os.path.isdir(os.path.join(BASEDIR, 'log')):
      raise


def log(info, console=True, save=False):
   now = str(datetime.datetime.now())[:19]
   if console:
      print('\n%s >>> %s\n' % (now, info), file=sys.stderr)
   if save:
      with open(LOG_FILE, 'a+') as log_file:
         print('\n%s >>> %s\n' % (now, info), file=log_file)


def send(event, url):
   try:
      post = requests.post(url, json=event)
      return post.status_code
   except Exception as e:
      return e


def parse_event(json_data, post_content=()):
   def _tag_users(text):
      get_tag = re.compile(r'\[\~(.*?)](.*)')
      tag = lambda token: get_tag.search(token) and '@%s%s' % (get_tag.search(token).group(1).lower(),
                                                 get_tag.search(token).group(2).lower()) or token
      return text and ' '.join(map(tag, text.split()))

   def _tag_files(text):
      get_tag = re.compile(r'\[\^(.*?)](.*)')
      tag = lambda token: get_tag.search(token) and 'file: %s%s' % (get_tag.search(token).group(1).lower(),
                                                     get_tag.search(token).group(2).lower()) or token
      return text and ' '.join(map(tag, text.split()))

   def _unfmt(text):
      get_tag = re.compile(r'{(.*?)}')
      tag = lambda token: '```' if get_tag.search(token) and get_tag.search(token).group(1) else token
      return text and ' '.join(map(tag, text.split()))

   if all(['webhookEvent' in json_data.keys(), 'issue' in json_data.keys()]):
      webevent = json_data['webhookEvent']
      display_name = json_data.get('user') and json_data['user'].get('displayName') or 'System'
      issue_id = json_data['issue']['key']
      issue_rest_url = json_data['issue']['self']
      get_url = re.compile(r'(.*?)\/rest\/api\/.*')
      issue_url = '%s/browse/%s' % (get_url.match(issue_rest_url).group(1), issue_id)
      summary = _tag_users(_tag_files(_unfmt(json_data['issue']['fields'].get('summary', ''))))
      description = _tag_users(_tag_files(_unfmt(json_data['issue']['fields'].get('description', ''))))
      issue_event_type_name = json_data.get('issue_event_type_name', '')

      priority = (json_data['issue']['fields'].get('priority') and
               json_data['issue']['fields']['priority']['name'] or 'empty')

      assignee = (json_data['issue']['fields'].get('assignee') and
               json_data['issue']['fields']['assignee']['displayName'] or 'empty')

      attachment = ()
      fields = ()
      attachment['username'] = JIMAM_USERNAME
      attachment['fields'] = fields

      attachment['author_link'] = issue_url
      m = re.search('.*(created|updated|deleted)', webevent)
      if m:
         attachment['author_name'] = issue_id + ' "' + summary + '" was ' + m.group(1) + ' by ' + display_name

         field = ()
         field['short'] = True
         field['title'] = 'Priority'
         field['value'] = priority
         fields.extend(field)

         field = ()
         field['short'] = True
         field['title'] = 'Assignee'
         field['value'] = assignee
         fields.extend(field)

      if 'changelog' in json_data.keys():
         changed_items = json_data['changelog']['items']
         for item in changed_items:
            field = item['field']
            from_value = item['fromString'] and _tag_users(_tag_files(_unfmt(item['fromString']))) or 'empty'
            to_value = item['toString'] and _tag_users(_tag_files(_unfmt(item['toString']))) or 'empty'

            field = ()
            field['title'] = field
            if field in ('summary', 'description'):
               field['short'] = False
               field['value'] = '> %s' % to_value
            else:
               field['short'] = True
               field['value'] = '~~%s~~&nbsp;&#10140;&nbsp;%s' % (from_value, to_value)
               
            fields.extend(field)

      if 'comment' in json_data.keys():
         comment = _tag_users(_tag_files(_unfmt(json_data['comment']['body'])))
         if issue_event_type_name in ('issue_commented',):
            field = ()
            field['short'] = False
            field['title'] = 'Comment'
            field['value'] = comment
            fields.extend(field)

   else:
      if DEBUG:
         log('Skipped. Raw: %s' % json_data, save=DEBUG)
      else:
         log('Do not want this. Skipped.')

   post_content['attachments'] = attachment

   return post_content

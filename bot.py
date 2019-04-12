#!/usr/bin/python3

import requests
import re
from random import randint
from datetime import datetime
import time
import telebot
import tokens
import conf


token = tokens.token
chat_id = tokens.chat_id


dir_path = '/home/donkey/rockBot/skwigelf'
#dir_path = './'

bot = telebot.TeleBot(token)

vktoken= tokens.vktoken
personal_token= tokens.personal_token

def clean_text(item):
    emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                u"\U00002702-\U000027B0"
                u"\U000024C2-\U0001F251"
                u"\U0001f926-\U0001f937"
                u'\U00010000-\U0010ffff'
                u"\u200d"
                u"\u2640-\u2642"
                u"\u2600-\u2B55"
                u"\u23cf"
                u"\u23e9"
                u"\u231a"
                u"\u3030"
                u"\ufe0f"
    "]+", flags=re.UNICODE)
    punctuation = re.compile(r"[\?\.\!]+(?=[\?\.\!])")
    hashtags = re.compile("#[A-Za-z0-9-a-яA-я\-\.\_]+")
    item=item.strip()
    item=re.sub(r'http\S+', '', item)
    item=re.sub(r'\[club(.*?)\|', '', item)
    item=re.sub(r'\[id(.*?)\|', '', item)
    item = emoji_pattern.sub(r'', item)
    item = hashtags.sub(r'', item)
    item = punctuation.sub(r'.', item)

    return item.replace('\n',' ').replace(']','')

def search_for_open_events(querry):
    city_id = 1
    group_ids = {}
    method='groups.search'
    r = requests.get('https://api.vk.com/method/'+ method,params={'offset':0, 'type':'event','future':1,'count':1000,'city_id': city_id ,'q':querry,'access_token':personal_token,'v':5.52})
    logger(r.status_code)
    if 'response' in r.json():
	    records = r.json()['response']['items']
	    print('Found {} events with querry "{}"'.format(len(records), querry))
	    for item in records:
	        if item['is_closed'] == 0:
	            group_ids[item['id']] = item['name']
	    print('Found {} not closed events with querry "{}"'.format(len(group_ids), querry))
	    return group_ids
    else:
        logger('Group search error: {}'.format(str(r.json())))
        return group_ids 



def get_event_descriptions_by_id(group_ids, n = 30):
    descriptions = {}
    ids = ','.join([str(item) for item in list(group_ids.keys())[:n]])
    ids_list = ids.split(',')
    method='groups.getById'
    fields = 'place,description,members_count,counters,start_date,finish_date, contacts, status'
    r = requests.get('https://api.vk.com/method/'+method,params={'group_ids':ids,'fields':fields,'access_token':vktoken,'v':5.52})
    description=r.json()
    for idx in range(len(description['response'])):
        items = {}
        if 'description' in  description['response'][idx]:
            if len(description['response'][idx]['description'].split()) < 10:
                continue
            items['description'] = clean_text(description['response'][idx]['description'])
        if 'place' in description['response'][idx]:
            if 'address' in  description['response'][idx]['place']:
                items['place'] = description['response'][idx]['place']['address']
        if 'start_date' in description['response'][idx]:
            items['time_stamp'] = description['response'][idx]['start_date']
            time=datetime.utcfromtimestamp(description['response'][idx]['start_date']).strftime('%Y-%m-%d %H:%M:%S')
            items['start_date'] = time
        if 'finish_date' in description['response'][idx]:
            time=datetime.utcfromtimestamp(description['response'][idx]['finish_date']).strftime('%Y-%m-%d %H:%M:%S')
            items['finish_date'] = time
            
        if 'name' in description['response'][idx]:
            items['name'] = description['response'][idx]['name']
        descriptions[ids_list[idx]] = items
    return descriptions



def make_records(description):
    texts = []
    min_post_len = conf.min_post_len
    max_post_len_sentences = conf.max_post_len_sentences
    for key in description:
        adress = ''
        start_date = ''
        end_date = ''
        link='vk.com/event' + key
        
        if 'name' in  description[key]:
            text = '{}: "{}" \n\n'.format(conf.start_phrases[randint(0,2)],description[key]['name'])
        else:
            text = ''
        
        text +='{} '.format('.'.join(description[key]['description'].split('.')[:max_post_len_sentences]))
        text += ' Продолжение по ссылке : {} \n\n'.format(link)
        if len(text.split()) < min_post_len:
            continue
        if 'start_date' in description[key]:
            start_date = description[key]['start_date']
            text += 'Начало {} в {} \n'.format(start_date.split(' ')[0], start_date.split(' ')[1][:5])
        if 'finish_date' in description[key]:
            finish_date = description[key]['finish_date']
            text += 'Окончание в {} \n'.format(finish_date.split(' ')[1][:5])
        if 'place' in description[key]:
            address = description[key]['place']
            text += 'Место проведения: {} \n'.format(address)
       
        texts.append(text)
    return texts

def log_posted(desc):
    f=open(dir_path+'/logged_records.log','a')
    for key in desc:
        f.write('{}{}\n'.format(key, desc[key]['time_stamp']))
    f.close()
    
def get_logs():
    f=open(dir_path+'/logged_records.log','r')
    logs=f.read().split('\n')
    f.close()
    return logs


def filter_desc(desc):
    records = dict()
    print('Filtering')
    try:
        logs = set(get_logs())
    except:
        logger('Logged records reading error')
        logs = []
    for key in desc:
        if str(key)+str(desc[key]['time_stamp']) in logs:
            continue
        else:
            records[key] = desc[key]
    return records

def logger(message):
    print(message)
    with open(dir_path+'/mainlog.log','a') as f:
        f.write('Time: {},{} \n'.format(datetime.now() , message))

def mainFunction(words):
    for keyword in words:
        group_ids  = search_for_open_events(keyword)
        if len(group_ids) > 0:
	        logger('Made group ids')
	        desc = get_event_descriptions_by_id(group_ids, 50)
	        logger('Recieved descriptions: {}, keyword : {} '.format(len(desc),keyword))
	        desc = filter_desc(desc)
	        log_posted(desc)
	        logger('Filtered records to post: {}, keyword: {} '.format(len(desc), keyword))
	        records_to_post = make_records(desc)
	        logger('Records to post: {} '.format(len(records_to_post)))
	        for record_to_post in records_to_post:
	            bot.send_message(chat_id, record_to_post)
	        logger('Sent messages by bot')
	    time.sleep(5)

with open(dir_path+'/keywords.txt','r') as f:
    key_words = f.read().split('\n')

key_words = [word for word in  key_words if word !='']

print(key_words,len(key_words))
mainFunction(key_words)


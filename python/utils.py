import regex as re
import yaml
from functools import lru_cache
import pymongo
from datetime import datetime
import regex as re
import os
from collections import defaultdict


@lru_cache(maxsize=1)
def get_config():
    with open('config.yml', 'r') as file:
        config = yaml.safe_load(file)
    return config


def get_db(config):
    uri = 'mongodb://{}:{}@{}:{}/?directConnection=true'.format(config['mongodb-user'],
                                          config['mongodb-passwd'],
                                          config['mongodb-host'],
                                          config['mongodb-port'])
    client = pymongo.MongoClient(uri)
    # client.drop_database(config['mongodb-db'])
    db = client[config['mongodb-db']]
    return (db[config['mongodb-collection']], db[config['mongodb-error-collection']])


def get_file_type(filename: str) -> str:
    filename = os.path.splitext(filename)[0]
    if re.fullmatch(r'\d+_\d+_p\d+', filename):
        return 'pixiv'
    elif re.fullmatch(r'\d+_p\d+', filename):
        return 'pixiv1'
    elif re.match(r'^twitter', filename):
        return 'twitter'
    elif re.match(r'^yande\.re', filename):
        return 'yandere'
    else:
        return 'other'


def extract_match(pattern: str, filename: str) -> dict:
    return match1.groupdict() if (match1 := re.match(pattern, filename)) else {}


def get_filename_info(filename: str, filetype: str) -> dict:
    nonedict = {
                    'user': None,
                    'userid': None,
                    'date': None,
                    'illustid': None,
                    'tags1': None,
                }
    match_dict = nonedict.copy()
    match filetype:
        case 'pixiv':
            pattern = r'(?P<userid>\d+)_(?P<illustid>\d+)_p\d+'
            match_dict |= extract_match(pattern, filename)
        case 'pixiv1':
            pattern = r'(?P<illustid>\d+)_p\d+'
            match_dict |= extract_match(pattern, filename)
        case 'yandere':
            pattern = r'yande\.re (?P<illustid>\d+)\s+(?P<tags1>.+)'
            match_dict |= extract_match(pattern, filename)
            if match_dict:
                match_dict['tags1'] = match_dict.pop('tags1').split()
        case 'twitter':
            pattern = r'twitter_(?P<user>.*?)(?:\(@(?P<userid>.*?)\))_(?P<date>\d{8}-\d{6})_(?P<illustid>\d+)_'
            match_dict |= extract_match(pattern, filename)
            if match_dict:
                try:
                    match_dict['date'] = datetime.strptime(match_dict['date'], '%Y%m%d-%H%M%S')
                except Exception:
                    match_dict['date'] = None
        case _:
            pass
    # if match_dict.get('userid') is not None:
    #     match_dict['userid'] = int(match_dict['userid'])
    # if match_dict.get('illustid') is not None:
    #     match_dict['illustid'] = int(match_dict['illustid'])
    
    return match_dict


operator_mapping = {
    '<': '$lt',
    '<=': '$lte',
    '>': '$gt',
    '>=': '$gte',
    '!=': '$ne'
}


def split_condition(condition):
    pattern = r'([<>!=]=?)\s*(\S+)'
    if match := re.match(pattern, condition):
        operator = match.group(1)
        value = match.group(2)
        return operator, value
    else:
        return None, None


def convert_value(key, val):
    if val.startswith('"') or val.startswith("'"):
        val = val[1:-1]
        return val
    if val == 'null':
        return None
    if key == 'date':
        return datetime.fromisoformat(val)
    return float(val) if '.' in val else int(val)


def build_query(params):
    query = defaultdict(dict)
    for param in params:
        if ';' in param:
            key, value = param.split(';', 1)
            for param1 in value.split('&'):
                op, val = split_condition(param1)
                if key == 'textlen':
                    query['text'] = {'$ne': None}
                    query['$expr'][operator_mapping[op]] = [{'$strLenCP': '$text'}, int(val)]
                    break
                val = convert_value(key, val)
                if op in operator_mapping:
                    query[key][operator_mapping[op]] = val
                elif op == '=':
                    query[key] = val
        elif param.startswith('tags1'):
            key, value = param.split(':', 1)
            query.setdefault('tags1', {}).setdefault('$all', []).append(value.strip())
        elif param.startswith('!tags1'):
            key, value = param.split(':', 1)
            query.setdefault('tags1', {}).setdefault('$nin', []).append(value.strip())
        elif param.startswith('!'):
            query[param[1:]] = {'$exists': False}
        else:
            query[param] = {'$exists': True}
    
    return dict(query)


def build_sort(params):
    query = defaultdict(dict)
    for param in params:
        if ';' in param:
            key, value = param.split(';', 1)
            if value == '1':
                query[key] = 1
            elif value == '-1':
                query[key] = -1
        else:
            query[param] = -1
    return dict(query)

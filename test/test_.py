#!/usr/bin/python3
#coding=utf-8

import pytest
import requests
import simplejson as json
import logging
import sys
import string
import time
from random import sample, choice
import base64
import os
from datetime import datetime, timedelta
CHARS = string.ascii_letters + string.digits

from hashids import Hashids

sys.path.append('lenfer')
from secret import get_secret, create_token
from db import DBConn, splice_params
from conf import CONF

sys.path.append('test')

DB = DBConn(CONF.items('db'))
DB.verbose = True
DB.connect()

API_URI = 'https://dev.lenfer.ru/api/'

LOGGER = logging.getLogger(__name__)

SECRET = get_secret(CONF.get('files', 'secret'))
def _create_token(data):
    return create_token(data, SECRET)
LOGIN = 'ADMIN'
PASSWORD = '18231823'

HASHIDS = Hashids(salt=SECRET.decode('utf-8'), min_length=6)

def rnd_string(length=8):
    return ''.join(choice(CHARS) for _ in range(length))

def update_data(data, update):
    if update:
        for field in update:
            if update[field] == '___DELETE___':
                del data[field]
            else:
                data[field] = update[field]

def cmp_data(db_data, post_data):
    assert db_data
    for key in post_data:
        assert key in db_data
        assert db_data[key] == post_data[key]

def test_register_login():
    user_data = {
        'login': 'test_reg_usr',
        'password': '11111111',
        'email': 'test@test.com'
        }
    DB.execute('delete from users where login = %(login)s', user_data)
    req = requests.post(API_URI + 'register_user', json=user_data)
    req.raise_for_status()
    srv_data = json.loads(req.text)
    assert srv_data
    assert srv_data['token']
    logging.getLogger().info(srv_data)
    db_user_data = DB.get_object('users', user_data, create=False)
    assert db_user_data
    for key in user_data:
        assert user_data[key] == db_user_data[key]
    req = requests.post(API_URI + 'register_user', json=user_data)
    assert req.status_code == 400
    LOGGER.debug(req.text)
    DB.execute('delete from users where login = %(login)s', user_data)
    req = requests.post(API_URI + 'register_user', json=user_data)
    req.raise_for_status()
    login = user_data['login']
    del user_data['login']
    req = requests.post(API_URI + 'register_user', json=user_data)
    assert req.status_code == 400
    user_data['login'] = login
    del user_data['email']
    req = requests.post(API_URI + 'login', json=user_data)
    req.raise_for_status()
    srv_data = json.loads(req.text)
    assert srv_data
    assert srv_data['token']
    user_data['password'] += '___'
    req = requests.post(API_URI + 'login', json=user_data)
    assert req.status_code == 400
    LOGGER.debug(req.text)
    del user_data['password']
    req = requests.post(API_URI + 'login', json=user_data)
    assert req.status_code == 400
    LOGGER.debug(req.text)
    DB.execute('delete from users where login = %(login)s', user_data)

def test_password_recovery_request():
    #request
    #--good user
    req = requests.post(API_URI + 'password_recovery_request', json={'login': LOGIN})
    req.raise_for_status()
    #--bad user
    req = requests.post(API_URI + 'password_recovery_request', json={'login': LOGIN + '_'})
    assert req.status_code == 400

def test_password_recovery():
    #change
    password = rnd_string()

    def post(update_token=None, update_post=None):
        data = {}
        token_data = {
            'login': LOGIN,
            'type': 'passwordRecovery',
            'expires': time.time() + 60 * 60 * 60}
        update_data(token_data, update_token)
        post_data = {'login': LOGIN,
            'token': _create_token(token_data),
            'password': password}
        update_data(post_data, update_post)
        return requests.post(API_URI + 'password_recovery', json=post_data)

    #--good request
    req = post()
    req.raise_for_status()
    db_user_data = DB.get_object('users', {'login': LOGIN}, create=False)
    assert db_user_data['password'] == password
    #--bad request
    #----expired
    req = post(update_token={'expires': time.time() - 1})
    assert req.status_code == 400
    logging.debug(req.text)
    #----missing expires field
    req = post(update_token={'expires': '___DELETE___'})
    assert req.status_code == 400
    logging.debug(req.text)
    #----wrong token type
    req = post(update_token={'type': 'blah'})
    assert req.status_code == 400
    logging.debug(req.text)
    #----missing token type
    req = post(update_token={'type': '___DELETE___'})
    assert req.status_code == 400
    logging.debug(req.text)
    #----wrong login
    req = post(update_token={'login': LOGIN + '_'})
    assert req.status_code == 400
    logging.debug(req.text)
    #----user not exists
    req = post(update_token={'login': LOGIN + '_'},update_post={'login': LOGIN + '_'})
    assert req.status_code == 400
    logging.debug(req.text)
    #----missing token
    req = post(update_post={'token': '___DELETE___'})
    assert req.status_code == 400
    logging.debug(req.text)
    DB.param_update('users', {'login': LOGIN}, {'password': PASSWORD})

def test_post_sensors_data():

    def post(update_token=None, update_post=None):
        data = {}
        token_data = {'device_id': 1}
        update_data(token_data, update_token)
        post_data = {'device_id': 1,
            'token': _create_token(token_data),
            'data': []}
        update_data(post_data, update_post)
        return requests.post(API_URI + 'sensors_data', json=post_data)

    #--good request
    data = [{
        'sensor_id': 1, 
        'tstamp': datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        'value': 300}]
    req = post(update_post={'data': data})
    req.raise_for_status()
    #--bad request
    #----wrong device_id in token
    req = post(update_token={'device_id': 2})
    assert req.status_code == 400
    logging.debug(req.text)
    #----device w/o sensors
    req = post(update_token={'device_id': 2}, update_post={'device_id': 2, 'data': data})
    assert req.status_code == 400
    logging.debug(req.text)

def test_register_device():

    def post(update_token=None, update_post=None):
        data = {}
        token_data = {'login': LOGIN, 'type': 'auth'}
        update_data(token_data, update_token)
        post_data = {'login': LOGIN,
            'token': _create_token(token_data),
            'device_hash': HASHIDS.encode(1)}
        update_data(post_data, update_post)
        return requests.post(API_URI + 'device/register', json=post_data)

    #--good request
    req = post()
    logging.debug(req.text)
    req.raise_for_status()

    #--device is already registerd - same user
    req = post()
    logging.debug(req.text)
    assert req.status_code == 400
    #--device is already registerd - same user
    req = post()
    logging.debug(req.text)
    assert req.status_code == 400
    #--device is already registerd - another user
    req = post(update_token={'login': LOGIN + '__'}, update_post={'login': LOGIN + '__'})
    logging.debug(req.text)
    assert req.status_code == 400
    #--no device id in db
    req = post(update_post={'device_hash': HASHIDS.encode(2)})
    logging.debug(req.text)
    assert req.status_code == 400
    #--bad hash
    req = post(update_post={'device_hash': 'aaaaaa'})
    logging.debug(req.text)
    assert req.status_code == 400

    DB.param_update('devices', {'id': 1}, {'login': None})

def test_get_sensor_data():
    post_data = {'sensor_id': 9,
        'begin': '2020-10-07 13:00',
        'end': '2020-10-07 14:00'}
    req = requests.post(API_URI + 'sensor/data', json=post_data)
    logging.debug(req.text)
    req.raise_for_status()
    data = json.loads(req.text)
    assert data
    assert data[0]
    assert data[0]['value']


def test_users_devices():

    def post(update_token=None, update_post=None):
        data = {}
        token_data = {'login': LOGIN, 'type': 'auth'}
        update_data(token_data, update_token)
        post_data = {'login': LOGIN, 'token': _create_token(token_data)}
        update_data(post_data, update_post)
        return requests.post(API_URI + 'users_devices', json=post_data)

    #--good request
    req = post()
    logging.debug(req.text)
    req.raise_for_status()

def test_device_schedules():

    token_data = {'login': LOGIN, 'type': 'auth'}

    def post_schedule(update_token=None, update_post=None, schedule_id='new'):
        data = {}
        update_data(token_data, update_token)
        post_data = {'login': LOGIN, 'token': _create_token(token_data)}
        update_data(post_data, update_post)
        return requests.post(API_URI + 'device_schedule/' + str(schedule_id),\
            json=post_data)

    def get_list():
        post_data = {'login': LOGIN, 'token': _create_token(token_data)}
        return requests.post(API_URI + 'users_device_schedules',\
            json=post_data)

    SCHEDULE = {'title': rnd_string(),\
        'device_type_id': 1,\
        'items': [\
            {'day_no': 1,\
                'params': {'foo': 'bar'}},\
            {'day_no': 2,\
                'params': {'foo': 'snafu'}}\
            ]}

    #create schedule
    req = post_schedule(update_post=SCHEDULE)
    logging.debug(req.text)
    req.raise_for_status()

    #get schedule list find id of the just created one
    req = get_list()
    logging.debug(req.text)
    req.raise_for_status()
    schedules = json.loads(req.text)
    schedule_from_srv = [x for x in schedules if x['title'] == SCHEDULE['title']][0]
    schedule_id = schedule_from_srv['id']

    #update schedule
    SCHEDULE['title'] = rnd_string()
    SCHEDULE['device_type_id'] = 2
    req = post_schedule(update_post=SCHEDULE, schedule_id=schedule_id)
    logging.debug(req.text)
    req.raise_for_status()

    #get detailed schedule data and check updates
    req = requests.get(API_URI + 'device_schedule/' + str(schedule_id))
    logging.debug(req.text)
    req.raise_for_status()
    schedule_from_srv = json.loads(req.text)
    assert SCHEDULE['title'] == schedule_from_srv['title']
    assert SCHEDULE['device_type_id'] == schedule_from_srv['device_type_id']
    assert len(schedule_from_srv['items']) == 2

    #delete schedule
    req = requests.delete(API_URI + 'device_schedule/' + str(schedule_id), 
            json={'login': LOGIN, 'token': _create_token(token_data)})
    logging.debug(req.text)
    req.raise_for_status()

    #check the schedule is no longer exists
    req = requests.get(API_URI + 'device_schedule/' + str(schedule_id))
    logging.debug(req.text)
    assert req.status_code == 400


def test_device_updates():

    DEVICE_ID = 15

    def post(update_token=None, update_post=None):
        data = {}
        token_data = {'device_id': DEVICE_ID}
        update_data(token_data, update_token)
        post_data = {'device_id': DEVICE_ID, 
            'token': _create_token(token_data),
            'schedule': {'hash': None, 'start': None}, 
            'props': {}
            }
        update_data(post_data, update_post)
        return requests.post(API_URI + 'device_updates', json=post_data)

    #--good request
    req = post()
    logging.debug(req.text)
    req.raise_for_status()

def test_device_log():

    def post(update_token=None, update_post=None):
        data = {}
        token_data = {'device_id': 1}
        update_data(token_data, update_token)
        post_data = {'device_id': 1,
            'token': _create_token(token_data),
            'entries': []}
        update_data(post_data, update_post )
        return requests.post(API_URI + 'devices_log/post', json=post_data)

    #--good request
    entries = [{
        'log_tstamp': (datetime.now() - timedelta(minutes=idx)).strftime("%m/%d/%Y, %H:%M:%S"),
        'txt': rnd_string(512)} for idx in range(2)]
    req = post(update_post={'entries': entries})
    req.raise_for_status()

    get_req_data = {'device_id': 1,
        'end': datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        'begin':  (datetime.now() - timedelta(hours=1)).strftime("%m/%d/%Y, %H:%M:%S")
    }
    req = requests.post(API_URI + 'devices_log', json=get_req_data)
    logging.debug(req.text)
    req.raise_for_status()
    data = json.loads(req.text)
    assert data
    assert data[-1]
    assert data[-1]['txt'] == entries[0]['txt'] 
    DB.execute('delete from devices_log where device_id = 1')


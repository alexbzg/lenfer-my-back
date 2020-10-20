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
from datetime import datetime
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
        return requests.post(API_URI + 'register_device', json=post_data)

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


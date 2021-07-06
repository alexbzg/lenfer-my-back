#!/usr/bin/python3
#coding=utf-8
"""creates device db record and outputs device id.json
postitional cmd line params:
    device type (integer id)
    owner's login (email)
    """
import argparse
import sys
import json

from hashids import Hashids

from secret import get_secret, create_token
from conf import CONF
from db import DBConn

PARSER = argparse.ArgumentParser(description="lenfer device creator")
PARSER.add_argument('type')
PARSER.add_argument('user', nargs='?')
ARGS = PARSER.parse_args()
DB = DBConn(CONF.items('db'))
DB.connect()

if not ARGS.type:
    sys.exit('Device type is required.')

PARAMS = {'device_type_id': ARGS.type, 'login': ARGS.user, 'props': []}
SECRET = get_secret(CONF['files']['secret']).decode('utf-8')
HASHIDS = Hashids(salt=SECRET, min_length=6)

DEVICE_TYPE_DATA = DB.execute("""
    select id, software_type, updates, props, modes 
        from devices_types 
        where id = %(device_type_id)s
    """, PARAMS)
if not DEVICE_TYPE_DATA:
    sys.exit('Invalid device type.')

if DEVICE_TYPE_DATA['modes']:
    PARAMS['mode'] = DEVICE_TYPE_DATA['modes'][0]['id']

def init_prop_value(prop):
    """creates device prop default value based on it's type"""
    value = None
    if prop['type'] == 'array':
        value = []
    elif prop['type'] == 'float_delta':
        value = [0, 0]
    return value

if DEVICE_TYPE_DATA['props']:
    PARAMS['props'] = json.dumps([init_prop_value(prop)\
            for prop in DEVICE_TYPE_DATA['props']])

DEVICE_DB_DATA = DB.get_object('devices', PARAMS, create=True)
DB.execute("""insert into sensors (device_type_sensor_id, device_id, is_master)
    select id, %(id)s, is_master
    from device_type_sensors
    where device_type_id = %(device_type_id)s""", DEVICE_DB_DATA)
DB.execute("""insert into devices_switches (device_id, device_type_switch_id)
    select %(id)s, id
    from device_type_switches
    where device_type_id = (select device_type_id 
        from devices
        where devices.id = %(id)s)""", DEVICE_DB_DATA)

DEVICE_DATA = {
    'id': DEVICE_DB_DATA['id'],
    'token': create_token({'device_id': DEVICE_DB_DATA['id']}, SECRET),
    'hash': HASHIDS.encode(DEVICE_DB_DATA['id']),
    'type': DEVICE_TYPE_DATA['software_type'],
    'updates': DEVICE_TYPE_DATA['updates']
    }

print(json.dumps(DEVICE_DATA))

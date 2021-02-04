#!/usr/bin/python3
#coding=utf-8

import argparse
import sys
import json

from hashids import Hashids

from secret import get_secret, create_token
from conf import CONF
from db import DBConn, splice_params

PARSER = argparse.ArgumentParser(description="lenfer device creator")
PARSER.add_argument('type')
PARSER.add_argument('user')
ARGS = PARSER.parse_args()
DB = DBConn(CONF.items('db'))
DB.connect()

if not ARGS.type:
    sys.exit('Device type is required.')

PARAMS = {'device_type_id': ARGS.type, 'login': ARGS.user}
SECRET = get_secret(CONF['files']['secret']).decode('utf-8')
HASHIDS = Hashids(salt=SECRET, min_length=6)


check_device_type = DB.execute("""
    select id 
        from devices_types 
        where id = %(device_type_id)s
    """, PARAMS)
if not check_device_type:
    sys.exit('Invalid device type.')
    
device_db_data = DB.get_object('devices', PARAMS, create=True)
DB.execute("""insert into sensors (device_type_sensor_id, device_id)
    select id, %(id)s
    from device_type_sensors
    where device_type_id = %(device_type_id)s""", device_db_data)
device_data = {
    'id': device_db_data['id'],
    'token': create_token({'device_id': device_db_data['id']}, SECRET),
    'hash': HASHIDS.encode(device_db_data['id'])
    }

print(json.dumps(device_data))


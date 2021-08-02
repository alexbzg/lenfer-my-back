#!/usr/bin/python3
#coding=utf-8

import json

from db import DBConn
from conf import CONF

DB = DBConn(CONF.items('db'))
DB.connect()

feeders_data = DB.execute("""
    select id, props 
    from devices
    where device_type_id = 3""")

for feeder_data in feeders_data:    
    for timer in feeder_data['props'][2]:
        timer.append(0)

    feeder_data['props'] = json.dumps(feeder_data['props'])

    DB.execute("""
        update devices 
        set props = %(props)s
        where id = %(id)s""", feeder_data)



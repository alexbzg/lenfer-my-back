#!/usr/bin/python3
#coding=utf-8

from db import DBConn
from conf import CONF

DB = DBConn(CONF.items('db'))
DB.connect()

DB.execute("""
insert into devices_log (device_id, rcvd_tstamp, log_tstamp, txt)
select id, disconnect_ts, disconnect_ts, 'disconnected' from 
	(select id, last_contact + interval '1 minute' as disconnect_ts  
	 from devices where last_contact < now() - interval '2 minutes') as devices_offline,
	 lateral (select txt from devices_log where device_id = devices_offline.id order by rcvd_tstamp desc limit 1) as last_log
where txt != 'disconnected'
""")

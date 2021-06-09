#!/usr/bin/python3
#coding=utf-8
"""onedif backend"""
import logging
import time
import json
import hashlib
from datetime import datetime

from flask import Flask, request, jsonify
from werkzeug.exceptions import InternalServerError
from hashids import Hashids

from validator import validate, bad_request
from db import DBConn, splice_params
from conf import CONF, APP_NAME, start_logging
from secret import get_secret, create_token
import send_email
from hash import data_hash

APP = Flask(APP_NAME)
APP.config.update(CONF['flask'])
APP.secret_key = get_secret(CONF['files']['secret'])
HASHIDS = Hashids(salt=APP.secret_key.decode('utf-8'), min_length=6)

with APP.app_context():
    start_logging('srv', CONF['logs']['srv_level'])
logging.debug('starting in debug mode')

DB = DBConn(CONF.items('db'))
DB.connect()
DB.verbose = True
APP.db = DB

def _create_public_id():
    user_count = DB.execute('select sum(1) from users;')
    return int(hashlib.sha256(str(user_count).encode('utf-8')).hexdigest(), 16)\
            % 10**6

def _create_token(data):
    return create_token(data, APP.secret_key)

@APP.errorhandler(InternalServerError)
def internal_error(exception):
    'Internal server error interceptor; logs exception'
    response = jsonify({'message': 'Server error'})
    response.status_code = 500
    logging.exception(exception)
    return response

@APP.route('/api/test', methods=['GET', 'POST'])
def test():
    """test if api is up"""
    return "Ok %s" % request.method

@APP.route('/api/register_user', methods=['POST'])
@validate(request_schema='login', recaptcha_field='recaptcha')
def register_user():
    """registers user and returns user data with token"""
    user_data = request.get_json()
    user_exists = DB.get_object('users', {'login': user_data['login']}, create=False)
    if user_exists:
        return bad_request('Пользователь с этим именем уже зарегистрирован.')
    user_data['public_id'] = _create_public_id()
    return send_user_data(splice_params(user_data, 'login', 'public_id', 'password'),\
        create=True)

@APP.route('/api/login', methods=['POST'])
@validate(request_schema='login')
def login():
    """checks login data and returns user data with token"""
    return send_user_data(splice_request('login', 'password'))

@APP.route('/api/user_data', methods=['POST'])
@validate(token_schema='auth', login=True)
def get_user_data():
    """returns user data by token"""
    return send_user_data(splice_request('login'))

@APP.route('/api/password_recovery_request', methods=['POST'])
@validate(request_schema='passwordRecoveryRequest', recaptcha_field='recaptcha')
def password_recovery_request():
    """check login data and returns user data with token"""
    req_data = request.get_json()
    user_data = DB.get_object('users', req_data, create=False)
    if not user_data or not user_data['email']:
        return bad_request('Пользователь или email не зарегистрирован.\n' +\
            'The username or email address is not registered.')
    token = _create_token({
        'login': req_data['login'],
        'type': 'passwordRecovery',
        'expires': time.time() + 60 * 60 * 60})
    text = """Пройдите по ссылкe, чтобы сменить пароль на ONEADIF.com: """\
        + CONF.get('web', 'address')\
        + '/#/passwordRecovery?token=' + token + """

Если вы не запрашивали смену пароля на ONEADIF.com, просто игнорируйте это письмо.
Ссылка будет действительна в течение 1 часа.

Follow this link to change your ONEADIF.com password: """ \
        + CONF.get('web', 'address')\
        + '/#/passwordRecovery?token=' + token + """

Ignore this message if you did not request password change


Служба поддержки ONEADIF.com support"""
    send_email.send_email(text=text,\
        fr=CONF.get('email', 'address'),\
        to=user_data['email'],\
        subject="ONEADIF.com - password change")
    return jsonify({'message':\
        'На ваш почтовый адрес было отправлено письмо с инструкциями по ' +\
        'сменен пароля.\n' +\
        'The message with password change instrunctions was sent to your ' +\
        'email address'})

def ok_response():
    return jsonify({'message': 'Ok'})

@APP.route('/api/password_recovery', methods=['POST'])
@validate(request_schema='login', token_schema='passwordRecovery',
          recaptcha_field='recaptcha', login=True)
def password_recovery():
    """sets new password after successfull recovery"""
    req_data = request.get_json()
    if not DB.param_update('users',\
        {'login': req_data['login']}, {'password': req_data['password']}):
        raise Exception('Password change failed')
    return ok_response()

@APP.route('/api/user/settings', methods=['POST'])
@validate(request_schema='post_user_settings', token_schema='auth', login=True)
def post_user_settings():
    """changes user's settings"""
    req_data = request.get_json()
    upd_params = {'timezone': req_data['timezone']}
    if req_data['password']:
        upd_params['password'] = req_data['password']
    if not DB.param_update('users', {'login': req_data['login']}, upd_params):
        raise Exception('Ошибка сохранения настроек.')
    return ok_response()

def update_device_last_contact(device_id):
    DB.execute("""
        update devices 
        set last_contact = now()
        where id = %(device_id)s""", {'device_id': device_id})

@APP.route('/api/device_updates', methods=['POST'])
@validate(request_schema='device_updates', token_schema='device')
def device_updates():
    """checks for update of device schedule/elegible props"""
    req_data = request.get_json()
    update_device_last_contact(req_data['device_id'])
    update_data = {}
    device_data = DB.execute("""
        select device_schedules.hash as schedule_hash, 
            device_schedules.id as schedule_id, 
            devices_types.schedule_params,
            device_schedules.params as schedule_settings,
            devices.props as props_values,
            devices_types.props as props_headers
        from devices join devices_types
            on devices.device_type_id = devices_types.id
            left join device_schedules
            on devices.schedule_id = device_schedules.id
        where devices.id = %(device_id)s""", req_data, keys=False)

    if 'schedule' in req_data:
        update_data['schedule'] = {'hash': None, 'start': None}
        if device_data and device_data['schedule_id']:
            schedule_start = None
            for idx, prop_header in enumerate(device_data['props_headers']):
                if 'schedule_start' in prop_header and prop_header['schedule_start']:
                    schedule_start = (datetime.strptime(device_data['props_values'][idx],\
                        "%Y-%m-%dT%H:%M:%S.%fZ").timetuple()\
                        if device_data['props_values'] and\
                            len(device_data['props_values']) > idx\
                        else None)
                    break
            if device_data['schedule_hash'] and schedule_start and\
                (device_data['schedule_hash'] != req_data['schedule']['hash']) or\
                (not req_data['schedule']['start'] or\
                [1 for i, j in zip(schedule_start, req_data['schedule']['start'])\
                    if i != j]):

                schedule = {
                    'params_list': [item['id'] for item in device_data['schedule_params']],\
                    'params': device_data['schedule_settings'],
                    'items': [item['params'] for item in schedule_items(device_data['schedule_id'])],\
                    'hash': device_data['schedule_hash'],\
                    'start': schedule_start}

                update_data['schedule'] = schedule

            else:
                del update_data['schedule']

    if 'props' in req_data:
        props_dict = props_list_to_dict(device_data['props_headers'], device_data['props_values'])
        logging.debug('props_dict')
        logging.debug(props_dict)
        update_props = [prop['id'] for prop in device_data['props_headers']
                        if 'device_updates' in prop and prop['device_updates']]

        srv_props = {prop: prop_value for prop, prop_value in props_dict.items()
                     if prop in update_props}
        sensors = DB.execute("""
            select device_type_sensor_id as id, enabled
            from sensors
            where device_id =%(device_id)s
            """, req_data, keys=False)
        srv_props['sensors'] = {row['id']: row['enabled'] for row in sensors} if sensors else {}

        switches = DB.execute("""
            select device_type_switch_id as id, enabled
            from devices_switches
            where device_id =%(device_id)s
            """, req_data, keys=False)
        srv_props['switches'] = {row['id']: row['enabled'] for row in switches} if switches else {}

        if data_hash(req_data['props']) != data_hash(srv_props):
            update_data['props'] = srv_props


    return jsonify(update_data)

def props_list_to_dict(headers, values):
    """converts device properties list from db to dictionary"""
    return {header['id']: (([\
        props_list_to_dict(header['items'], item)\
            for item in values[idx]])\
        if 'items' in header else values[idx])\
        for idx, header in enumerate(headers)}


@APP.route('/api/switches_state', methods=['POST'])
@validate(request_schema='post_switches_state', token_schema='device')
def post_switches_state():
    """stores device switches state in db"""
    req_data = request.get_json()
    update_device_last_contact(req_data['device_id'])
    device_rtc = DB.execute("""
        select rtc 
        from devices_types join devices 
            on devices.device_type_id = devices_types.id
        where devices.id = %(device_id)s
        """, req_data)
    for item in req_data['data']:
        if not device_rtc:
            del item['tstamp']
        item['device_id'] = req_data['device_id']
        DB.get_object('devices_switches_state', item, create=True)
    return ok_response()


@APP.route('/api/sensors_data', methods=['POST'])
@validate(request_schema='post_sensors_data', token_schema='device')
def post_sensors_data():
    """stores sensors data in db"""
    req_data = request.get_json()
    update_device_last_contact(req_data['device_id'])
    device_sensors = DB.execute("""
        select device_type_sensor_id as id, id as sensor_id 
            from sensors 
            where device_id = %(device_id)s
        """, req_data, keys=True)
    if device_sensors:
        device_rtc = DB.execute("""
            select rtc 
            from devices_types join devices 
                on devices.device_type_id = devices_types.id
            where devices.id = %(device_id)s
            """, req_data)
        for item in req_data['data']:
            if item['sensor_id'] in device_sensors.keys():
                item['sensor_id'] = device_sensors[item['sensor_id']]['sensor_id']
                if not device_rtc:
                    del item['tstamp']
                DB.get_object('sensors_data', item, create=True)
    else:
        return bad_request('Device sensors not found')
    return ok_response()

@APP.route('/api/devices_log/post', methods=['POST'])
@validate(request_schema='post_devices_log', token_schema='device')
def post_devices_log():
    """stores devices log entries in db"""
    req_data = request.get_json()
    update_device_last_contact(req_data['device_id'])
    for entry in req_data['entries']:
        entry['device_id'] = req_data['device_id']
        DB.get_object('devices_log', entry, create=True)
    return ok_response()

@APP.route('/api/devices_log', methods=['POST'])
def get_devices_log():
    """returns device log for period in json"""
    req_data = request.get_json()
    data = DB.execute("""
        select to_char(log_tstamp, 'YYYY-MM-DD HH24:MI:SS') as log_tstamp,
            to_char(rcvd_tstamp, 'YYYY-MM-DD HH24:MI:SS') as rcvd_tstamp,
            txt
            from devices_log
            where device_id = %(device_id)s and
                log_tstamp between %(begin)s and %(end)s
            order by log_tstamp desc
        """, req_data, keys=False)
    if isinstance(data, dict):
        data = [data,]
    return jsonify(data)

@APP.route('/api/users_device/public/<public_id>', methods=['GET'])
def get_users_devices_public(public_id):
    """returns json users devices list
    [{id, title, type_id, type_title}]
    by his public_id
    """
    public_id = public_id.lower()    
    devices_data = DB.execute("""
        select devices.id, device_type_id as type_id, 
            devices_types.title as type_title,
            schedule_id,
            devices.title as title
            from devices join devices_types 
                on device_type_id = devices_types.id join users 
                on devices.login = users.login
            where users.public_id = %(public_id)s and devices.public_access
            order by devices.title
        """, {'public_id': public_id}, keys=False)
    if isinstance(devices_data, dict):
        devices_data = [devices_data,]
    elif not devices_data:
        devices_data = []
    return jsonify(devices_data)

@APP.route('/api/users_devices', methods=['POST'])
@validate(token_schema='auth', login=True)
def users_devices():
    """returns json users devices list
    [{id, title, type_id, type_title}]
    """
    req_data = request.get_json()
    devices_data = DB.execute("""
        select devices.id, device_type_id as type_id, 
            devices_types.title as type_title,
            schedule_id, public_access,
            devices.title as title
            from devices join devices_types 
                on device_type_id = devices_types.id
            where devices.login = %(login)s
            order by devices.title
        """, req_data, keys=False)
    if isinstance(devices_data, dict):
        devices_data = [devices_data,]
    elif not devices_data:
        devices_data = []
    for device in devices_data:
        device['hash'] = HASHIDS.encode(device['id'])
    return jsonify(devices_data)

def send_devices_status(login=None, public_id=None):
    """sends json users by login or public_id (public access only) 
    devices last connect timestamp list
    {id: timestamp}"""
    sql = """
        select devices.id, 
            last_contact::timestamptz as last_tstamp
            from devices """
    sql += """join users 
                on devices.login = users.login
            where users.public_id = %(public_id)s and devices.public_access
        """ if public_id else "where devices.login = %(login)s"
    devices_data = DB.execute(sql, {'public_id': public_id, 'login': login},\
        keys=True)
    if not devices_data:
        devices_data = {}
    return jsonify(devices_data)

@APP.route('/api/devices_status/public/<public_id>', methods=['GET'])
def devices_status_public(public_id):
    """returns json user's public devices last connect timestamp list"""
    return send_devices_status(public_id=public_id.lower())

@APP.route('/api/devices_status', methods=['POST'])
@validate(token_schema='auth', login=True)
def devices_status():
    """returns json logged user's devices last connect timestamp list"""
    req_data = request.get_json()
    return send_devices_status(login=req_data['login'])

@APP.route('/api/users_device_schedules', methods=['POST'])
@validate(token_schema='auth', login=True)
def users_device_schedules():
    """returns json users devices_schedules detailed list
    [{id, title, device_type_id, device_type_title,
        items: [{no, params: {}}]}]
    """
    req_data = request.get_json()
    schedules = DB.execute("""
        select device_schedules.id, device_type_id as device_type_id, 
            device_schedules.title, devices_types.title as device_type_title
            from device_schedules join devices_types 
                on device_type_id = devices_types.id
            where device_schedules.login = %(login)s
        """, req_data, keys=False)
    if not schedules:
        schedules = []
    if isinstance(schedules, dict):
        schedules = [schedules,]
    for schedule in schedules:
        schedule['items'] = schedule_items(schedule['id'])
    return jsonify(schedules)

def schedule_items(schedule_id):
    """returns dict of schedule's items by schedule's id"""
    items = DB.execute("""
        select day_no, params
            from device_schedule_items
            where schedule_id = %(id)s
            order by day_no
        """, {'id': schedule_id}, keys=False)
    if isinstance(items, dict):
        items = [items,]
    return items

@APP.route('/api/device/<device_id>', methods=['GET'])
def get_device_info(device_id):
    """returns device info json"""
    device_id = int(device_id)
    device_data = DB.execute("""
        select device_type_id as device_type_id, 
            devices_types.title as device_type,
            devices.title as title, 
            schedule_id, 
            devices_types.props as props_titles,
            devices.props as props_values
            from devices join devices_types 
                on device_type_id = devices_types.id
            where devices.id = %(device_id)s
        """, {'device_id': device_id}, keys=False)
    if not device_data:
        return bad_request('Устройство не найдено. Device not found.')
    timezone_ts, timezone_dev, timezone_srv = get_timezones(device_id=device_id)
    device_data['hash'] = HASHIDS.encode(device_id)
    device_data['sensors'] = DB.execute("""
		select * from
		(select sensors.id, sensors.is_master, sensor_type as type, device_type_sensor_id,
					sensors.title as title, device_type_sensors.title as default_title,
					sensors.enabled, sensors.correction
				from sensors join device_type_sensors on
						device_type_sensors.id = sensors.device_type_sensor_id
						where device_id = %(device_id)s) as sensors
					left join lateral (select value,
						to_char(tstamp::timestamp at time zone %(timezone_ts)s 
                            at time zone %(timezone_dev)s, 'YYYY-MM-DD HH24:MI:SS') as tstamp
						from sensors_data
							where sensor_id = sensors.id
						order by tstamp desc
						limit 1) as last_data 
						on true
        order by device_type_sensor_id
        """, {'device_id': device_id, 'timezone_ts': timezone_ts, 'timezone_dev': timezone_dev}, keys=False)
    device_data['switches'] = DB.execute("""
		select * from
		(select device_type_switch_id as id,
					devices_switches.title as title, device_type_switches.title as default_title,
					enabled, device_type_switches.type
				from devices_switches join device_type_switches on
						device_type_switches.id = devices_switches.device_type_switch_id
						where device_id = %(device_id)s) as switches
					left join lateral (select state,
						to_char(tstamp, 'YYYY-MM-DD HH24:MI:SS') as tstamp
						from devices_switches_state
							where devices_switches_state.device_id = %(device_id)s
                                and devices_switches_state.device_type_switch_id = switches.id
						order by tstamp desc
						limit 1) as last_data 
						on true
        order by id
        """, {'device_id': device_id}, keys=False)

    return jsonify(device_data)

@APP.route('/api/devices_types', methods=['GET'])
def get_devices_types():
    """returns devices_types info json"""
    devices_types_data = DB.execute("""
        select * from devices_types
        """, keys=False)
    return jsonify(devices_types_data)


@APP.route('/api/device_schedule/<schedule_id>', methods=['GET'])
def get_schedule_data(schedule_id):
    """returns device schedule itesm (days) in json"""
    schedule_id = int(schedule_id)
    schedule_data = DB.execute("""
        select device_schedules.id, device_type_id as device_type_id, 
            device_schedules.title, devices_types.title as device_type_title,
            device_schedules.params
            from device_schedules join devices_types 
                on device_type_id = devices_types.id
            where device_schedules.id = %(schedule_id)s
        """, {'schedule_id': schedule_id}, keys=False)
    if not schedule_data:
        return bad_request('Шаблон не найден.')
    schedule_data['items'] = schedule_items(schedule_id)
    return jsonify(schedule_data)


@APP.route('/api/device_schedule/<schedule_id>', methods=['DELETE'])
@validate(token_schema='auth', login=True)
def delete_schedule(schedule_id):
    """deletes device schedule from db"""
    error = None
    req_data = request.get_json()
    schedule_id = int(schedule_id)
    check_schedule = DB.execute("""
        select login 
        from device_schedules
        where id = %(id)s""", {'id': schedule_id}, keys=False)
    if check_schedule:
        if check_schedule == req_data['login']:
            DB.execute("""
                delete from device_schedule_items
                where schedule_id = %(schedule_id)s
                """, {'schedule_id': schedule_id})
            DB.param_delete('device_schedules', {'id': schedule_id})
        else:
            error = 'Шаблон зарегистрирован другим пользователем.'
    else:
        error = 'Шаблон не найден.'
    if error:
        return bad_request(error)
    else:
        return ok_response()

@APP.route('/api/device_schedule/<schedule_id>', methods=['POST'])
@validate(request_schema='post_device_schedule', token_schema='auth', login=True)
def post_schedule_data(schedule_id):
    """saves new/edited device schedule to db"""
    error = None
    req_data = request.get_json()
    req_data['hash'] = hashlib.md5(json.dumps(req_data, sort_keys=True).encode('utf-8')).hexdigest()
    if schedule_id == 'new':
        schedule = DB.get_object('device_schedules',\
            splice_params(req_data, 'login', 'title', 'device_type_id', 'hash', 'params'),\
            create=True)
        if schedule:
            schedule_id = schedule['id']
        else:
            raise Exception('Ошибка создания шаблона.')
    else:
        schedule_id = int(schedule_id)
        check_schedule = DB.execute("""
            select login 
            from device_schedules
            where id = %(id)s""", {'id': schedule_id}, keys=False)
        if check_schedule:
            if check_schedule == req_data['login']:
                DB.param_update('device_schedules',\
                    {'id': schedule_id},\
                    splice_params(req_data, 'title', 'device_type_id', 'hash', 'params'))
                DB.execute("""
                    delete from device_schedule_items
                    where schedule_id = %(schedule_id)s
                    """, {'schedule_id': schedule_id})
            else:
                error = 'Шаблон зарегистрирован другим пользователем.'
        else:
            error = 'Шаблон не найдено.'
    if error:
        return bad_request(error)
    else:
        DB.execute("""
            insert into device_schedule_items (schedule_id, day_no, params)
            values (%(schedule_id)s, %(day_no)s, %(params)s)""",\
            [{'schedule_id': schedule_id,\
                'day_no': item['day_no'],\
                'params': json.dumps(item['params'])}\
                for item in req_data['items']])
        return jsonify({'id': schedule_id})

@APP.route('/api/user/public', methods=['POST'])
@validate(request_schema='post_user_public_settings', token_schema='auth', login=True)
def post_user_public_settings():
    """saves updated user's public_id and devices public access settings to db"""
    req_data = request.get_json()
    if not DB.param_update('users', {'login': req_data['login']},\
        {'public_id': req_data['public_id']}):
        raise Exception('Ошибка сохранения настроек.')
    for item in req_data['devices']:
        item['login'] = req_data['login']
    DB.execute("""
        update devices
        set public_access = %(public_access)s
        where id = %(id)s and login = %(login)s
        """, req_data['devices'])
    return ok_response()

@APP.route('/api/device/<device_id>', methods=['POST'])
@validate(request_schema='post_device_props', token_schema='auth', login=True)
def post_device_props(device_id):
    """saves updated device title/props to db"""
    device_id = int(device_id)
    req_data = request.get_json()
    error = None
    check_device = DB.execute("""
        select login, devices_types.props as props_headers
            from devices join devices_types
                on devices.device_type_id = devices_types.id
            where devices.id = %(id)s""", {'id': device_id}, keys=False)
    if check_device:
        if check_device['login'] == req_data['login']:
            upd_params = {}
            if 'delete' in req_data and req_data['delete']:
                upd_params = {'login': None}
            else:

                timers_prop_id = None
                for index, item in enumerate(check_device['props_headers']):
                    if item['id'] == 'timers':
                        timers_prop_id = index
                        break
                if timers_prop_id and req_data['props'][timers_prop_id]:
                    req_data['props'][timers_prop_id].sort(key=lambda item: item[0])

                upd_params = {'title': req_data['title'],\
                    'schedule_id': req_data['schedule_id']\
                        if 'schedule_id' in req_data else None,\
                    'props': json.dumps(req_data['props'])}
            DB.param_update('devices', {'id': device_id}, upd_params)
        else:
            error = 'Устройство зарегистрировано другим пользователем.'
    else:
        error = 'Устройство не найдено.'
    if error:
        return bad_request(error)
    else:
        return ok_response()

@APP.route('/api/sensor/<sensor_id>', methods=['POST'])
@validate(request_schema='post_sensor_props', token_schema='auth', login=True)
def post_sensor_settings(sensor_id):
    """updates sensor title and other settings"""
    sensor_id = int(sensor_id)
    req_data = request.get_json()
    error = None
    check_sensor = DB.execute("""
        select login 
        from sensors join devices on sensors.device_id = devices.id
        where sensors.id = %(id)s""", {'id': sensor_id}, keys=False)
    if check_sensor:
        if check_sensor == req_data['login']:
            DB.param_update('sensors',\
                {'id': sensor_id},\
                {'title': req_data['title'],\
                    'enabled': req_data['enabled'],\
                    'correction': req_data['correction'],
                    'is_master': req_data['is_master']})
        else:
            error = 'Датчик зарегистрирован другим пользователем.'
    else:
        error = 'Датчик не найден.'
    if error:
        return bad_request(error)
    else:
        return ok_response()

@APP.route('/api/switch/<device_id>/<switch_id>', methods=['POST'])
@validate(request_schema='post_switch_props', token_schema='auth', login=True)
def post_switch_settings(device_id, switch_id):
    """updates switch title and other settings"""
    device_id = int(device_id)
    switch_id = int(switch_id)
    req_data = request.get_json()
    error = None
    check_switch = DB.execute("""
        select login 
        from devices join devices_switches 
            on devices.id = devices_switches.device_id
        where devices.id = %(device_id)s and 
            devices_switches.device_type_switch_id = %(switch_id)s""",\
        {'device_id': device_id, 'switch_id': switch_id}, keys=False)
    if check_switch:
        logging.debug('check_switch')
        logging.debug(check_switch)
        if check_switch == req_data['login']:
            DB.param_update('devices_switches',\
                {'device_id': device_id, 'device_type_switch_id': switch_id},\
                {'title': req_data['title'],\
                    'enabled': req_data['enabled']})
        else:
            error = 'Датчик зарегистрирован другим пользователем.'
    else:
        error = 'Датчик не найден.'
    if error:
        return bad_request(error)
    else:
        return ok_response()



@APP.route('/api/sensor/<sensor_id>', methods=['GET'])
def get_sensor_info(sensor_id):
    """returns sensor info json"""
    sensor_id = int(sensor_id)
    sensor_data = DB.execute("""
        select sensors.title as sensor_title, 
                device_type_sensors.title as device_type_title,
                sensor_type, correction
            from sensors join device_type_sensors
                on device_type_sensor_id = device_type_sensors.id
            where sensors.id = %(sensor_id)s
        """, {'sensor_id': sensor_id}, keys=False)
    if not sensor_data:
        return bad_request('Сенсор не найден. Sensor not found.')
    return jsonify(sensor_data)

def get_timezones(device_id=None, sensor_id=None):
    device_data = DB.execute("""
        select rtc, users.timezone
            from sensors join devices on sensors.device_id = devices.id
                join devices_types on devices.device_type_id = devices_types.id 
                join users on users.login = devices.login
            where (%(sensor_id)s is null or sensors.id = %(sensor_id)s) and
                (%(device_id)s is null or devices.id = %(device_id)s)
            limit 1

    """, {'sensor_id': sensor_id, 'device_id': device_id}, keys=False)
    timezone_ts = device_data['timezone'] if device_data['rtc']  else\
        CONF['server']['timezone']
    timezone_dev = device_data['timezone']
    return (timezone_ts, timezone_dev, CONF['server']['timezone'])

@APP.route('/api/sensor/data', methods=['POST'])
def get_sensor_data():
    """returns sensor's data for period in json"""
    req_data = request.get_json()

    req_data['timezone_ts'], req_data['timezone_dev'], req_data['timezone_srv'] =\
        get_timezones(sensor_id=req_data['sensor_id'])

    data = DB.execute("""
        select to_char(tstamp::timestamp at time zone %(timezone_ts)s at time zone %(timezone_dev)s,
            'YYYY-MM-DD HH24:MI:SS') as tstamp, value
        from sensors_data
            where sensor_id = %(sensor_id)s and
                tstamp 
                    between 
                        ((now() - interval %(interval)s)::timestamp at time zone %(timezone_srv)s 
                            at time zone %(timezone_ts)s) and 
                        (now()::timestamp at time zone %(timezone_srv)s at time zone %(timezone_ts)s)
            order by tstamp
        """, req_data, keys=False)
    return jsonify(data)

@APP.route('/api/switch/state', methods=['POST'])
def get_switch_state():
    """returns switch's state for period in json"""
    req_data = request.get_json()

    req_data['timezone_ts'], req_data['timezone_dev'], req_data['timezone_srv'] =\
        get_timezones(device_id=req_data['device_id'])

    data = DB.execute("""
        select to_char(tstamp::timestamp at time zone %(timezone_ts)s at time zone %(timezone_dev)s,
            'YYYY-MM-DD HH24:MI:SS') as tstamp, state
            from devices_switches_state
            where device_id = %(device_id)s and 
                device_type_switch_id = %(device_type_switch_id)s and
                    tstamp between 
                        ((now() - interval %(interval)s)::timestamp at time zone %(timezone_srv)s 
                            at time zone %(timezone_ts)s) and 
                        (now()::timestamp at time zone %(timezone_srv)s at time zone %(timezone_ts)s)
            order by tstamp
        """, req_data, keys=False)
    return jsonify(data)

@APP.route('/api/device/create', methods=['POST'])
@validate(request_schema='register_device', token_schema='auth', login=True)
def create_device():
    """registers device and it's sensors data in db;
    returns json {"device_id": _, "device_token": _}"""
    req_data = request.get_json()
    check_device_type = DB.execute("""
        select id 
            from devices_types 
            where id = %(device_type_id)s
        """, req_data)
    if not check_device_type:
        return bad_request('Неверный тип устройства. Invalid device type.')
    else:
        device_db_data = DB.get_object('devices',\
            splice_request("login", "device_type_id"), create=True)
        DB.execute("""insert into sensors (device_type_sensor_id, device_id)
            select id, %(id)s
            from device_type_sensors
            where device_type_id = %(device_type_id)s""", device_db_data)
        token = _create_token({'device_id': device_db_data['id']})
        return jsonify({'device_id': device_db_data['id'], 'device_token': token})


@APP.route('/api/device/register', methods=['POST'])
@validate(request_schema='register_device', token_schema='auth', login=True)
def register_device():
    """binds device to user's account"""
    req_data = request.get_json()
    device_id = HASHIDS.decode(req_data['device_hash'])
    error = None
    if device_id:
        check_device = DB.execute("""
            select id, login 
                from devices
                where id = %(device_id)s
            """, {'device_id': device_id}, False)
        if check_device:
            if check_device['login']:
                if check_device['login'] == req_data['login']:
                    error = 'Вы уже зарегистрировали это устройство.\n' +\
                            'You had already registered this device.'
                else:
                    error = 'Устройство уже зарегистрировано дркгим пользователем.\n' +\
                            'Another user had already registered this device.'
            else:
                DB.param_update('devices', {'id': device_id}, {'login': req_data['login']})
        else:
            error = 'Устройство не найдено. Device not found.'
    else:
        error = 'Неверный код устройства. Invalid device code.'
    if error:
        return bad_request(error)
    else:
        return ok_response()

def splice_request(*params):
    return splice_params(request.get_json(), *params)

def send_user_data(user_data, create=False):
    """returns user data with auth token as json response"""
    data = DB.get_object('users', user_data, create=create)
    if data:
        token = _create_token({'login': data['login'], 'type': 'auth'})
        del data['password']
        data['token'] = token
        return jsonify(data)
    else:
        if create:
            raise Exception("User creation failed")
        else:
            return bad_request('Неверное имя пользователя или пароль.\n' +\
                    'Wrong username or password')

if __name__ == "__main__":
    APP.run(host='127.0.0.1', port=5001)

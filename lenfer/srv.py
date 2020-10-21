#!/usr/bin/python3
#coding=utf-8
"""onedif backend"""
import logging
import time

from flask import Flask, request, jsonify
from werkzeug.exceptions import InternalServerError
from hashids import Hashids

from validator import validate, bad_request
from db import DBConn, splice_params
from conf import CONF, APP_NAME, start_logging
from secret import get_secret, create_token
import send_email

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
        return bad_request('Пользователь с этим именем уже зарегистрирован.\n' +\
                'This username is already exists.')
    return send_user_data(user_data, create=True)

@APP.route('/api/login', methods=['POST'])
@validate(request_schema='login')
def login():
    """check login data and returns user data with token"""
    return send_user_data(request.get_json())

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
@validate(request_schema='login', token_schema='passwordRecovery', recaptcha_field='recaptcha',\
        login=True)
def password_recovery():
    """check login data and returns user data with token"""
    req_data = request.get_json()
    if not DB.param_update('users',\
        {'login': req_data['login']}, {'password': req_data['password']}):
        raise Exception('Password change failed')
    return ok_response()

@APP.route('/api/sensors_data', methods=['POST'])
@validate(request_schema='post_sensors_data', token_schema='device')
def post_sensors_data():
    """stores sensors data in db"""
    req_data = request.get_json()
    device_sensors = DB.execute("""
        select device_type_sensor_id as id, id as sensor_id 
            from sensors 
            where device_id = %(device_id)s
        """, req_data, keys=True)
    if device_sensors:
        for item in req_data['data']:
            if item['sensor_id'] in device_sensors.keys():
                item['sensor_id'] = device_sensors[item['sensor_id']]['sensor_id']
                DB.get_object('sensors_data', item, create=True)
    else:
        return bad_request('Device sensors not found')
    return ok_response()


@APP.route('/api/users_devices', methods=['POST'])
@validate(token_schema='auth')
def users_devices():
    """returns json users devices list
    [{id, title, type_id, type_title}]
    """
    req_data = request.get_json()
    devices_data = DB.execute("""
        select devices.id, device_type_id as type_id, 
            devices_types.title as type_title,
            devices.title as title
            from devices join devices_types 
                on device_type_id = devices_types.id
            where devices.login = %(login)s
        """, req_data, keys=False)
    if isinstance(devices_data, dict):
        devices_data = [devices_data,]
    elif not devices_data:
        devices_data = []
    return jsonify(devices_data)

@APP.route('/api/device/<device_id>', methods=['GET'])
def get_device_info(device_id):
    """returns device info json"""
    device_id = int(device_id)
    device_data = DB.execute("""
        select device_type_id as device_type_id, 
            devices_types.title as device_type,
            devices.title as title
            from devices join devices_types 
                on device_type_id = devices_types.id
            where devices.id = %(device_id)s
        """, {'device_id': device_id}, keys=False)
    if not device_data:
        return bad_request('Устройство не найдено. Device not found.')
    device_data['sensors'] = DB.execute("""
        select id 
            from sensors 
            where device_id = %(device_id)s
        """, {'device_id': device_id}, keys=False)
    return jsonify(device_data)

@APP.route('/api/sensor/<sensor_id>', methods=['GET'])
def get_sensor_info(sensor_id):
    """returns sensor info json"""
    sensor_id = int(sensor_id)
    sensor_data = DB.execute("""
        select sensors.title as sensor_title, 
                device_type_sensors.title as device_type_title,
                sensor_type
            from sensors join device_type_sensors
                on device_type_sensor_id = device_type_sensors.id
            where sensors.id = %(sensor_id)s
        """, {'sensor_id': sensor_id}, keys=False)
    if not sensor_data:
        return bad_request('Сенсор не найден. Sensor not found.')
    return jsonify(sensor_data)

@APP.route('/api/sensor/data', methods=['POST'])
def get_sensor_data():
    """returns sensors data for period in json"""
    req_data = request.get_json()
    data = DB.execute("""
        select to_char(tstamp, 'YYYY-MM-DD HH24:MI:SS') as tstamp,  value
            from sensors_data 
            where sensor_id = %(sensor_id)s and
                tstamp between %(begin)s and %(end)s
        """, req_data, keys=False)
    return jsonify(data)

@APP.route('/api/create_device', methods=['POST'])
@validate(request_schema='register_device', token_schema='auth')
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


@APP.route('/api/register_device', methods=['POST'])
@validate(request_schema='register_device', token_schema='auth')
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

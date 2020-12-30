#!/usr/bin/python3
#coding=utf-8
import argparse
import os
import sys
import hashlib

from json_utils import save_json, load_json
from hash import data_hash

PARSER = argparse.ArgumentParser(description="lenfer device software index builder")
PARSER.add_argument('path')
ARGS = PARSER.parse_args()

if not ARGS.path:
    sys.exit('Path is required.')

if not os.path.isdir(ARGS.path):
    sys.exit('Path does not exist')

INDEX_PATH = os.path.join(ARGS.path, 'index.json')
SOFTWARE_ROOT_PATH = os.path.join(ARGS.path, 'software')
INDEX = load_json(INDEX_PATH)
if not INDEX:
    INDEX = {}
DEVICES_TYPES = {}

for root, dirs, files in os.walk(SOFTWARE_ROOT_PATH):
    for file_name in files:
        file_path = os.path.join(root, file_name)
        file_web_path = os.path.relpath(file_path, SOFTWARE_ROOT_PATH)
        print(file_web_path)
        file_hash = None
        with open(file_path, 'rb') as file_handle:
            file_hash = hashlib.md5(file_handle.read()).hexdigest()
        if not file_web_path in INDEX:
            INDEX[file_web_path] = {}
        INDEX[file_web_path]['hash'] = file_hash
        if 'devices_types' in INDEX[file_web_path]:
            for type in INDEX[file_web_path]['devices_types']:
                if type not in DEVICES_TYPES:
                    DEVICES_TYPES[type] = None

for device_type in DEVICES_TYPES:
    DEVICES_TYPES[device_type] = data_hash({file: data for file, data in INDEX.items()\
            if 'devices_types' not in data or device_type in data['devices_types']})

DEVICES_TYPES['base'] = data_hash({file: data for file, data in INDEX.items()\
    if 'devices_types' not in data})

save_json(INDEX, INDEX_PATH, indent=4)
save_json(DEVICES_TYPES, os.path.join(ARGS.path, 'devices.json'))

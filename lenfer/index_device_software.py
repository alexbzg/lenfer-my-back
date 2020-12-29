#!/usr/bin/python3
#coding=utf-8
import argparse
import os
import sys
import hashlib

from json_utils import save_json, load_json

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

save_json(INDEX, INDEX_PATH, indent=4)


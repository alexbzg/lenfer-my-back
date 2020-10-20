#!/usr/bin/python3
#coding=utf-8

import argparse
import sys

from hashids import Hashids

from secret import get_secret, create_token
from conf import CONF


PARSER = argparse.ArgumentParser(description="lenfer device token/hash generator")
PARSER.add_argument('id')
ARGS = PARSER.parse_args()

if not ARGS.id:
    sys.exit('Device id is required.')

SECRET = get_secret(CONF['files']['secret']).decode('utf-8')
HASHIDS = Hashids(salt=SECRET, min_length=6)

print(create_token({'device_id': int(ARGS.id)}, SECRET))
print(HASHIDS.encode(int(ARGS.id)))

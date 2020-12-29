#!/usr/bin/python
#coding=utf-8

import hashlib
import json

def data_hash(data):
    """returns definitive data hash for changes tracking"""
    return hashlib.md5(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()

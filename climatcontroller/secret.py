#!/usr/bin/python3
#coding=utf-8

import os
import base64
import logging

import jwt

def get_secret(fpath):
    """read secret from filepath, in file not exists creates random and stores to filepath"""
    res = None
    if os.path.isfile(fpath):
        with open(fpath, 'rb') as f_secret:
            res = f_secret.read()
    if not res:
        res = base64.b64encode(os.urandom(64))
        with open(fpath, 'wb') as f_secret:
            f_secret.write(res)
    return res

def create_token(data, secret):
    """creates web token"""
    try:
        return jwt.encode(data, secret, algorithm='HS256').decode('utf-8')
    except Exception:
        logging.exception('Token generation error')
        return None

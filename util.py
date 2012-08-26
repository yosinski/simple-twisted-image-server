#! /usr/bin/env python

import hashlib

import settings



def computeHash(path, secretKey, hashLength):
    return hashlib.sha1(secretKey + path).hexdigest()[:hashLength]

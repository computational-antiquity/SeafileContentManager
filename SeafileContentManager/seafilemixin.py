#! python3
# -*- coding: utf-8 -*-

from datetime import datetime
import os
import sys
import requests
import json
import nbformat
import subprocess

from tornado import web

BASE = os.path.expanduser("~") + os.path.sep + '.seafileCM' + os.path.sep

try:
    os.makedirs(BASE, mode=0o740, exist_ok=True)
except:
    raise print('Can not create settings dir. ')


def getConnection():
    """Read credentials for Seafile endpoint.

    Routines to establish the connection to the Seafile Instance,
    check credentials, and retriev the library ID.
    """
    try:
        with open(BASE + 'settings', 'r') as file:
            data = file.read()
        seafileURL = data.split(',')[0].strip()
    except:
        seafileURL = os.environ.get('SEAFILE_URL', '')
        writeData = True

    try:
        with open(BASE + 'settings','r') as file:
            data = file.read()
        token = data.split(',')[1].strip()
    except:
        token = os.environ.get('SEAFILE_ACCESS_TOKEN', '')

    try:
        with open(BASE + 'settings','r') as file:
            data = file.read()
        libraryName = data.split(',')[2].strip()
    except:
        libraryName = ''

    print(seafileURL)
    print(token)
    print(libraryName)

    if writeData:
        with open(BASE + 'settings', 'a') as file:
            file.write('{0},{1}'.format(seafileURL, token))

    # Seafile URL
    if seafileURL == '':
        raise ValueError("Please set the SEAFILE_URL environment variable")

    # Access Token
    if token == '':
        raise ValueError("Please set the SEAFILE_ACCESS_TOKEN environment variable")

    authHeader = {"Authorization": "Token {0}".format(token)}
    # check Authorization
    res = requests.get(seafileURL + '/api2/auth/ping/', headers=authHeader)
    assert res.text == '"pong"', 'Wrong token {0}, cannot access API at {1}.'.format(token, seafileURL + '/api2')
    # Destination library
    libraryName = os.environ.get('SEAFILE_LIBRARY', 'notebooks')
    if libraryName != '':
        pass
    else:
        libraryName = 'notebooks'
    resLib = requests.get(seafileURL + '/api2/repos/', headers=authHeader)
    idList = [x['id'] for x in resLib.json() if x['name'] == libraryName]
    try:
        # check if idList has one element = library ID exists
        assert 0 < len(idList) < 2, 'Cannot find specified library: {0}'.format(libraryName)
        libraryID = idList[0]
    except:
        # if not, create new library with name libraryName
        data = {'name': libraryName, 'desc': 'new library'}
        createLib = requests.post(
            seafileURL + '/api2/repos/',
            headers=authHeader, data=data
            )
        assert createLib.status_code == 200, 'Cannot create new library, error code {0}'.format(createLib.status_code)
        libraryID = createLib.json()['repo_id']
    # general information of seafile instance, not used yet
    serverInfo = requests.get(seafileURL + '/api2/server-info').json()
    #
    return (seafileURL, authHeader, libraryID, libraryName, serverInfo)

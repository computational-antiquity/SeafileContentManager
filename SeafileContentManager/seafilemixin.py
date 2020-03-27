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
    # Routines to establish the connection to the Seafile Instance,
    # check credentials, and retriev the library ID.

    try:
        with open(BASE + 'settings','r') as file:
            data = file.read()
        seafileURL = data.split(',')[0].strip()
    except:
        seafileURL = ''

    try:
        with open(BASE + 'settings','r') as file:
            data = file.read()
        token = data.split(',')[1].strip()
    except:
        token = ''

    try:
        with open(BASE + 'settings','r') as file:
            data = file.read()
        libraryName = data.split(',')[2].strip()
    except:
        libraryName = ''

    print(seafileURL)
    print(token)
    print(libraryName)

    # Seafile URL
    seafileURL = os.environ.get('SEAFILE_URL', '')
    if seafileURL != '':
        pass
    else:
        seafileURL = 'https://keeper.mpdl.mpg.de'
        #seafileURLBase = subprocess.check_output(["zenity","--entry","--text",'Please provide the basic Seafile URL (e.g. https://repo.seafile.com):',"--title",'Seafile URL?','--display=:0'])
        #seafileURL = seafileURLBase.decode("utf-8").strip()
        #print(seafileURL)
        # os.environ['SEAFILE_URL'] = seafileURL
        # raise ValueError("Please set the SEAFILE_URL environment variable")
    # Access Token
    token = os.environ.get('SEAFILE_ACCESS_TOKEN','')
    if token != '':
        pass
    else:
        seafileAccount = subprocess.check_output(["zenity","--password","--username","--text",'Please provide your account informations once to obtain an access token:',"--title",'Seafile Account?','--display=:0']).decode("utf-8")
        account = seafileAccount.split('|')
        res = requests.post(seafileURL + "/api2/auth-token/", data={'username': account[0], 'password': account[1]})
        assert res.status_code == 200, 'Could not obtain access token using your credentials.'
        token = res.json()['token']
        with open(BASE + 'settings','a') as file:
            file.write('{0},{1}'.format(seafileURL, token))
        # os.environ['SEAFILE_ACCESS_TOKEN'] = token
        #print(token)
        #raise ValueError("Please set the SEAFILE_ACCESS_TOKEN environment variable")
    authHeader = {"Authorization":"Token {0}".format(token)}
    # check Authorization
    res = requests.get(seafileURL + '/api2/auth/ping/', headers = authHeader)
    assert res.text == '"pong"', 'Wrong token {0}, cannot access API at {1}.'.format(token, seafileURL + '/api2')
    # Destination library
    libraryName = os.environ.get('SEAFILE_LIBRARY', 'notebooks')
    if libraryName != '':
        pass
    else:
        libraryName = 'notebooks'
        #raise ValueError("Please set the SEAFILE_LIBRARY environment variable")
    #libraryName = libraryName
    #
    resLib = requests.get(seafileURL + '/api2/repos/', headers = authHeader)
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
            headers = authHeader, data = data
            )
        assert createLib.status_code == 200, 'Cannot create new library, error code {0}'.format(createLib.status_code)
        libraryID = createLib.json()['repo_id']
    # general information of seafile instance, not used yet
    serverInfo = requests.get(seafileURL + '/api2/server-info').json()
    #
    return (seafileURL, authHeader, libraryID, libraryName, serverInfo)

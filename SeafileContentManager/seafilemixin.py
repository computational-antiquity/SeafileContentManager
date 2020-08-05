#! python3
# -*- coding: utf-8 -*-

import os
import requests

BASE = os.path.expanduser("~") + os.path.sep + '.seafileCM' + os.path.sep

try:
    os.makedirs(BASE, mode=0o740, exist_ok=True)
except:
    raise print('Can not create settings dir. ')


def checkToken(url, token):
    authHeader = {"Authorization": "Token {0}".format(token)}
    res = requests.get(url + '/api2/auth/ping/', headers=authHeader)
    message = 'Wrong token {0}, cannot access API at {1}.'.format(
        token, url + '/api2')
    assert res.text == '"pong"', message
    return


def checkNotEmpty(url, token):
    if url == '':
        raise ValueError(
            "Please set the SEAFILE_URL environment variable"
            )
    elif token == '':
        raise ValueError(
            "Please set the SEAFILE_ACCESS_TOKEN environment variable"
            )
    else:
        pass


def getLibraryID(url, token, lib='notebooks'):
    authHeader = {"Authorization": "Token {0}".format(token)}
    resLib = requests.get(url + '/api2/repos/', headers=authHeader)
    idList = [x['id'] for x in resLib.json() if x['name'] == lib]
    try:
        # check if idList has one element = library ID exists
        errorMsg = 'Cannot find specified library: {0}'.format(lib)
        assert 0 < len(idList) < 2, errorMsg
        libraryID = idList[0]
    except:
        # if not, create new library with name libraryName
        data = {'name': lib, 'desc': 'new library'}
        createLib = requests.post(
            url + '/api2/repos/',
            headers=authHeader, data=data
            )
        errorMsg = 'Cannot create new library, error code {0}'.format(
            createLib.status_code
            )
        assert createLib.status_code == 200, errorMsg
        libraryID = createLib.json()['repo_id']
    return libraryID


def getSeafileVS(url):
    vs = requests.get(url + '/api2/server-info').json()['version']
    mainVs = int(vs.split('.')[0])
    return mainVs


def getConnection():
    """Read credentials for Seafile endpoint.

    Routines to establish the connection to the Seafile Instance,
    check credentials, and retrieve the library ID.
    """

    resetCreds = os.environ.get('SEAFILE_CREDENTIALS_RESET', False)
    if resetCreds == 'True':
        seafileURL = os.environ.get('SEAFILE_URL', '')
        token = os.environ.get('SEAFILE_ACCESS_TOKEN', '')
        libraryName = os.environ.get('SEAFILE_LIBRARY', 'notebooks')
        checkToken(seafileURL, token)
        authHeader = {"Authorization": "Token {0}".format(token)}
        seafileVs = getSeafileVS(seafileURL)
        if seafileVs < 7:
            libraryID = getLibraryID(seafileURL, token, libraryName)
        else:
            libraryID = ''
        with open(BASE + 'settings', 'w') as file:
            file.write('{0}, {1}, {2}'.format(seafileURL, token, libraryName))
        return (seafileURL, authHeader, libraryID, libraryName, seafileVs)

    try:
        libraryName = ''
        with open(BASE + 'settings', 'r') as file:
            data = file.read().split(',')
        parts = [x.strip().strip('\n') for x in data]
        if len(parts) == 3:
            if parts[2] != '':
                seafileURL, token, libraryName = parts
            else:
                seafileURL, token = parts[:2]
        elif len(parts) == 2:
            seafileURL, token = parts
        checkNotEmpty(seafileURL, token)
    except:
        seafileURL = os.environ.get('SEAFILE_URL', '')
        token = os.environ.get('SEAFILE_ACCESS_TOKEN', '')
        libraryName = os.environ.get('SEAFILE_LIBRARY', '')
        checkNotEmpty(seafileURL, token)
        with open(BASE + 'settings', 'w') as file:
            file.write('{0},{1},{2}'.format(seafileURL, token, libraryName))
    authHeader = {"Authorization": "Token {0}".format(token)}
    seafileVs = getSeafileVS(seafileURL)
    if seafileVs < 7:
        checkToken(seafileURL, token)
        libraryID = getLibraryID(seafileURL, token, libraryName)
    else:
        libraryID = ''
    return (seafileURL, authHeader, libraryID, libraryName, seafileVs)

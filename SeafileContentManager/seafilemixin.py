from datetime import datetime
import os
import sys
import requests
import json
import nbformat

from tornado import web

def getConnection():
    # Routines to establish the connection to the Seafile Instance,
    # check credentials, and retriev the library ID.
    #
    # Seafile URL
    seafileURL = os.environ.get('SEAFILE_URL', '')
    if seafileURL != '':
        pass
    else:
        raise ValueError("Please set the SEAFILE_URL environment variable")
    # Access Token
    token = os.environ.get('SEAFILE_ACCESS_TOKEN','')
    if token != '':
        pass
    else:
        raise ValueError("Please set the SEAFILE_ACCESS_TOKEN environment variable")
    authHeader = {"Authorization":"Token {0}".format(token)}
    # check Authorization
    res = requests.get(seafileURL + '/api2/auth/ping/', headers = authHeader)
    assert res.text == '"pong"', 'Wrong token {0}, cannot access API at {1}.'.format(token, seafileURL + '/api2')
    # Destination library
    libraryName = os.environ.get('SEAFILE_LIBRARY', '')
    if libraryName != '':
        pass
    else:
        raise ValueError("Please set the SEAFILE_LIBRARY environment variable")
    resLib = requests.get(seafileURL + '/api2/repos/', headers = authHeader)
    idList = [x['id'] for x in resLib.json() if x['name'] == libraryName]
    # check if idList has one element = library ID
    assert 0 < len(idList) < 2, 'Cannot find specified library: {0}'.format(libraryName)
    # general information of seafile instance, not used yet
    serverInfo = requests.get(seafileURL + '/api2/server-info').json()
    # basic settings
    libraryID = idList[0]
    libraryName = libraryName
    #
    return (seafileURL, authHeader, libraryID, libraryName, serverInfo)

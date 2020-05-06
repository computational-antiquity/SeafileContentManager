#! python3
# -*- coding: utf-8 -*-
from datetime import datetime

from .seamanager import SeafileContentManager
from .seafilemixin import getConnection


class SeafileFS(SeafileContentManager):
    """A os-like filesystem manager for Seafile.

    Maps queries like listdir to calls to the Seafile API.
    """

    def __init__(self, *args, **kwargs):
        retVals = getConnection()

        self.seafileURL = retVals[0]
        self.authHeader = retVals[1]
        self.libraryID = retVals[2]
        self.libraryName = retVals[3]
        self.serverInfo = retVals[4]

    def _getCWD(self):
        pass

    def listdir_attrib(self, path=None):
        """List dir content with attributes."""
        files = self.makeRequest('/dir/?p={0}'.format(path)).json()
        fileList = []
        for fileDict in files:
            res = {}
            res['last_modified'] = datetime.fromtimestamp(
                fileDict['mtime']
                )
            res['name'] = fileDict['name']
            filepath = path + '/' + fileDict['name']
            res['path'] = filepath.lstrip('/')
            if fileDict['permission'] == 'rw':
                res['writeable'] = True
            else:
                res['writeable'] = False
            if fileDict['type'] == 'file':
                res['size'] = fileDict['size']
                try:
                    fileType = res['name'].split('.')[1]
                    if fileType == 'ipynb':
                        res['type'] = 'notebook'
                    else:
                        res['type'] = 'file'
                except:
                    res['type'] = 'file'
            elif fileDict['type'] == 'dir':
                res['type'] = 'directory'
            fileList.append(res)
        return fileList

    def listdir(self, path=None):
        """List dir content."""
        files = self.makeRequest('/dir/?p={0}'.format(path)).json()
        fileNames = [x['name'] for x in files]
        return fileNames

    def isfile(self, path=None):
        """Return file True or False."""
        try:
            ret = self.makeRequest(
                '/file/detail/?p={0}'.format(path)
            )
            if ret.status_code == 404:
                return False
            if ret.status_code == 200:
                return True
        except:
            pass
        return False

    def open(self, path, mode='r'):
        """Open file as byte or str object."""

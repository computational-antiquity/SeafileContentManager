#! python3
# -*- coding: utf-8 -*-
import errno
import os
from datetime import datetime

from .seamanager import SeafileContentManager
from .seafilemixin import getConnection


class SeafileFS(SeafileContentManager):
    """A os-like filesystem manager for Seafile.

    Maps queries like listdir to calls to the Seafile API.
    """

    def __init__(self):
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

    def mkdir(self, path=None):
        pass

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

        if mode in ('w','w+'):
            return SeafileFileModel(path, mode)
        elif self.file_exists(path):
            return SeafileFileModel(path, mode)
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), path
        )


class SeafileFileModel(SeafileContentManager):
    """Return file like model for Seafile API."""

    def __init__(self, path, mode):
        retVals = getConnection()

        self.seafileURL = retVals[0]
        self.authHeader = retVals[1]
        self.libraryID = retVals[2]
        self.libraryName = retVals[3]
        self.serverInfo = retVals[4]

        self.filePath = path
        self.fileMode = mode
        if self.fileMode in ('w', 'w+'):
            # TODO: Create empty file model
            pass
        else:
            self.fileModel = self.getFileModel(path)

    def read(self):
        """Read file from Seafile API."""
        if self.fileMode in ('a','r', 't', 'rt'):
            return self.fileModel['content']
        if self.fileMode in ('b', 'b+', 'r+b'):
            return self.fileModel['content'].encode()

    def readlines(self):
        return self.fileModel['content'].splitlines(True)

    def write(self, content):
        if self.fileMode == 'a':
            oldcontent = self.fileModel['content']
            contentDict = {
                'content': oldcontent + content
            }
            self.fileModel.update(contentDict)

            self.save(self.fileModel, self.filePath)
        elif self.fileMode in ('w', 'w+'):
            contentDict = {
                'content': content
            }
            self.fileModel.update(contentDict)

            self.save(self.fileModel, self.filePath)
        else:
            raise OSError('Not implemented.')

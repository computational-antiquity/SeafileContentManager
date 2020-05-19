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
        model = {
            'content': None,
            'format': None,
            'mimetype': None,
            'type': 'directory',
            'name': path.split('/')[-1],
            'writable': True,
            'last_modified': datetime.now(),
            'path': path,
            'created': datetime.now(),
            'size': '',
            }
        self.save(model, path)

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
        """
        Open file as byte or str object.

        Possible modes are
            r (default): read existing file
            a: append to existing file or create new
            w: overwrite existing or create new
            b: open as binary data

            adding a + sign allows to also read in
            a+: read starts at end (not yet implemented)
            r+: read starts at beginning
            w+: truncate
        """
        if mode in ['r', 'r+', 'b', 'r+b']:
            if self.file_exists(path):
                return SeafileFileModel(path, mode)
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )
        if mode in ('x', 'x+', 'x+b'):
            if self.file_exists(path):
                raise FileExistsError(
                    errno.EEXIST, os.strerror(errno.EEXIST), path
                )
            return SeafileFileModel(path, mode)
        if mode in ['a', 'a+', 'a+b', 'w', 'w+', 'w+b']:
            return SeafileFileModel(path, mode)
        if mode == 'b+':
            raise ValueError(
                "Must have exactly one of create/read/write/append\
                 mode and at most one plus: '{0}'".format(mode)
            )
        raise ValueError("invalid mode: '{0}'".format(mode))


class SeafileFileModel(SeafileContentManager):
    """Return file like model for Seafile API."""

    def __init__(self, path, mode):
        retVals = getConnection()

        self.seafileURL = retVals[0]
        self.authHeader = retVals[1]
        self.libraryID = retVals[2]
        self.libraryName = retVals[3]
        self.serverInfo = retVals[4]
        self.rawModel = {
            'content': '',
            'format': None,
            'mimetype': 'text/plain',
            'type': 'file',
            'name': path.split('/')[-1],
            'writable': True,
            'last_modified': datetime.now(),
            'path': path,
            'created': datetime.now(),
            'size': '',
            }

        self.filePath = path
        self.fileMode = mode
        if self.fileMode == 'r':
            self.fileModel = self.getFileModel(path)
        elif self.fileMode == 'x':
            self.fileModel = self.rawModel
        elif self.fileMode in ['a', 'a+', 'a+b', 'w', 'w+', 'w+b']:
            if self.file_exists(path):
                self.fileModel = self.getFileModel(path)
                if self.fileModel in ['w', 'w+', 'w+b']:
                    contentDict = {
                        'content': ''
                    }
                    self.fileModel.update(contentDict)
                    self.save(self.fileModel, self.filePath)
            else:
                self.fileModel = self.rawModel

    def read(self):
        """Read file from Seafile API."""
        if self.fileMode in ('r', 'a+', 'w+'):
            return self.fileModel['content']
        if self.fileMode in ('b', 'r+b', 'a+b', 'w+b'):
            return self.fileModel['content'].encode()
        if self.fileMode in ('w', 'x'):
            raise ValueError(
                "Can not read in '{0}' file mode".format(self.fileMode)
            )

    def readlines(self):
        """Read all lines on file."""
        lines = self.fileModel['content'].splitlines(True)
        if self.fileMode in ('b', 'r+b', 'a+b', 'w+b', 'x+b'):
            return [x.encode() for x in lines]
        return lines

    def write(self, content):
        """Write file to Seafile backend."""
        if self.fileMode in ('r+', 'r+b', 'a', 'a+', 'a+b'):
            oldcontent = self.fileModel['content']
            contentDict = {
                'content': oldcontent + content
            }
            self.fileModel.update(contentDict)
            self.save(self.fileModel, self.filePath)
        elif self.fileMode in ('x+', 'x+b', 'w', 'w+', 'w+b'):
            contentDict = {
                'content': content
            }
            self.fileModel.update(contentDict)
            self.save(self.fileModel, self.filePath)
        elif self.fileMode in ('r', 'b', 'x'):
            raise ValueError("Can not write in '{0}' file mode.".format(
                self.fileMode
            ))

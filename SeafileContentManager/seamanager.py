import datetime
import os
import sys
import requests
import json
import nbformat

from notebook.services.contents.manager import ContentsManager

class SeafileContentManager(ContentsManager):
    """
    A replacement ContentsManager for Jupyter Notebooks to use Seafiles WebAPI v2.
    Assumes three env variables set:

        SEAFILE_ACCESS_TOKEN: see https://manual.seafile.com/develop/web_api.html#quick-start
        SEAFILE_API_URL: e.g. https://sub.domain.com/api2
        SEAFILE_LIBRARY: Library name, ID is determined automatically for API calls

    """
    def __init__(self, *args, **kwargs ):
        # API URL
        seafileAPIURL = os.environ.get('SEAFILE_API_URL', '')
        if seafileAPIURL != '':
            pass
        else:
            raise ValueError("Please set the SEAFILE_API_URL environment variable")
        # Token
        token = os.environ.get('SEAFILE_ACCESS_TOKEN','')
        if token != '':
            pass
        else:
            raise ValueError("Please set the SEAFILE_ACCESS_TOKEN environment variable")
        self.authHeader = {"Authorization":"Token {0}".format(token)}
        res = requests.get(seafileAPIURL + '/auth/ping/', headers = self.authHeader)
        assert res.text == '"pong"', 'Wrong token {0}, cannot access API at {1}.'.format(token,seafileAPIURL)
        # Destination library
        libraryName = os.environ.get('SEAFILE_LIBRARY', '')
        if libraryName != '':
            pass
        else:
            raise ValueError("Please set the SEAFILE_LIBRARY environment variable")
        resLib = requests.get(seafileAPIURL + '/repos/', headers = self.authHeader)
        idList = [x['id'] for x in resLib.json() if x['name'] == libraryName]
        assert 0 < len(idList) < 2, 'Cannot find specified library: {0}'.format(libraryName)

        self.libraryID = idList[0]
        self.baseURL = seafileAPIURL + '/repos/{0}'.format(self.libraryID)

    def makeRequest(self, apiPath):
        url = self.baseURL + apiPath
        res = requests.get(url, headers = self.authHeader)
        return res

    def getDirModel(self, path):
        files = self.makeRequest('/dir/?p={0}'.format(path)).json()
        fileList = []
        for fileDict in files:
            res = {}
            res['created'] = datetime.datetime.fromtimestamp(fileDict['mtime'])
            res['name'] = fileDict['name']
            filepath =  path + '/' + fileDict['name']
            res['path'] = filepath.lstrip('/')
            if fileDict['permission'] == 'rw':
                res['writeable'] = True
            else:
                res['writeable'] = False
            if fileDict['type'] == 'file':
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
            res['format'] = None
            res['mimetype'] = None
            res['content'] = None
            fileList.append(res)
        retDir = {'content': fileList, 'format': 'json', 'mimetype': None}
        return retDir


    def getFileModel(self, filePath, content = True):
        file = self.makeRequest('/file/detail/?p={0}'.format(filePath)).json()
        retFile = {}
        dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
        fileData = requests.get(dlLink.json())
        retFile['type'] = 'file'
        retFile['name'] = file['name']
        retFile['path'] = filePath.lstrip('/')
        retFile['created'] = datetime.datetime.fromtimestamp(file['mtime'])
        retFile['content'] = None
        try:
            fileType = file['name'].split('.')[1]
        except:
            fileType = ''
        if fileType in ['txt','md']:
            retFile['format'] = 'text'
            retFile['mimetype'] = 'text/plain'
            if content:
                retFile['content'] = fileData.content.decode('utf8')
        elif fileType == 'ipynb':
            retFile['format'] = 'json'
            retFile['mimetype'] = None
            if content:
                cont = nbformat.reads(fileData.content.decode('utf8'),as_version=4)
                retFile['content'] = cont

        else:
            retFile['format'] = 'base64'
            retFile['mimetype'] = 'application/octet-stream'
            if content:
                retFile['content'] = fileData.content.decode('utf8')
        return retFile

    def operateOnFile(self,filePath, action, params=False):
        url = self.baseURL + '/file/?p={0}'.format(filePath)
        data = {'operation':action}
        if params:
            for parSet in params:
                data[parSet[0]] = parSet[1]
        res = requests.post(url, headers = self.authHeader, data=data)
        return res

    def dir_exists(self, path):
        res = self.makeRequest('/dir/?p=/{0}'.format(path))
        if res.status_code == 404:
            return False
        elif res.status_code == 200:
            return True
        elif res.status_code == 440:
            raise ValueError('Folder is encrypted: {0}'.format(path))
        elif res.status_code == 520:
            raise ValueError('Operation failed.')
        else:
            pass

    def is_hidden(self, path):
        objects = path.split('/')
        obj = objects[-1]
        if obj and obj.startswith('.'):
            return True
        elif obj:
            return False
        else:
            raise ValueError('Cannot find object: {0}'.format(path))

    def file_exists(self, path):
        res = self.makeRequest('/file/history/?p={0}'.format(path))
        if res.status_code == 404:
            return False
        elif res.status_code == 200:
            return True



    def get(self, path, content=True, type=None, format=None):
        try:
            fileTrue = path.split('/')[-1].split('.')[1]
        except:
            fileTrue = ''
        if fileTrue:
            try:
                return self.getFileModel(path, content)
            except:
                return self.getDirModel(path)
        else:
            try:
                return self.getDirModel(path)
            except:
                return self.getFileModel(path, content)

    def save(self, model, path):
        pass

    def delete_file(self, path):
        pass

    def rename_file(self, old_path, new_path):
        res = self.operateOnFile(old_path, 'rename',('newname', new_path))
        if res.status_code in [301, 404]:
            return
        else:
            raise AttributeError('Operation failed, returned {0}'.format(res.status_code))

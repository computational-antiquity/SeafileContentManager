import datetime
import os
import sys
import requests
import json
import nbformat

from tornado import web

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

        self.serverInfo = requests.get(seafileAPIURL + '/server-info').json()

        self.libraryID = idList[0]
        self.libraryName = libraryName
        self.baseURL = seafileAPIURL + '/repos/{0}'.format(self.libraryID)

        self.baseModel = {
            'name': "",
            'path': "",
            'last_modified': "",
            'created': "",
            'content': "",
            'format': "",
            'mimetype': "",
            'size': ""
        }

    def makeRequest(self, apiPath):
        url = self.baseURL + apiPath
        res = requests.get(url, headers = self.authHeader)
        return res

    def getDirModel(self, path, content=True):
        files = self.makeRequest('/dir/?p={0}'.format(path)).json()
        if content:
            try:
                fileList = []
                for fileDict in files:
                    res = {}
                    res['last_modified'] = datetime.datetime.fromtimestamp(fileDict['mtime'])
                    res['name'] = fileDict['name']
                    filepath =  path + '/' + fileDict['name']
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
                    res['format'] = None
                    res['mimetype'] = None
                    res['content'] = None
                    fileList.append(res)
            ## Empty folder have no content, list nothing...
            except:
                fileList = None
        else:
            fileList = None
        ## Only sub-folder in fileList have a creation date.
        ## Folder details (name, mtime, siz, etc) of current folder_path can
        ## be obtained from api/v2.1 which is not allways implemented.
        ## See https://manual.seafile.com/develop/web_api_v2.1.html#get-directory-detail
        retDir = {
            'content': fileList, 'format': 'json', 'mimetype': None,
            'type':'directory','name':None,'writable':True,'last_modified':datetime.datetime.now(),
            'path':path, 'created': datetime.datetime.now()
            }
        return retDir


    def getFileModel(self, filePath, content = True):
        file = self.makeRequest('/file/detail/?p={0}'.format(filePath)).json()
        retFile = {}
        dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
        if not "error_msg" in dlLink.json().keys():
            fileData = requests.get(dlLink.json())

        retFile['type'] = 'file'
        try:
            retFile['name'] = file['name']
        except:
            retFile['name'] = ''
        retFile['path'] = filePath.lstrip('/')
        try:
            retFile['created'] = datetime.datetime.fromtimestamp(file['mtime'])
        except:
            retFile['created'] = datetime.datetime.now()
        retFile['content'] = None
        # TODO: replace Dummy values
        retFile['last_modified'] = 12
        retFile['writable'] = True
        try:
            fileType = file['name'].split('.')[-1]
        except:
            fileType = ''
        if fileType in ['txt','md']:
            retFile['format'] = 'text'
            retFile['mimetype'] = 'text/plain'
            if content:
                retFile['content'] = fileData.content.decode('utf8')
        elif fileType == 'ipynb':
            retFile['type'] = 'notebook'
            retFile['format'] = 'json'
            retFile['mimetype'] = None
            if content:
                cont = nbformat.reads(fileData.content.decode('utf8'), as_version=4)
                retFile['content'] = cont
        else:
            retFile['format'] = 'base64'
            retFile['mimetype'] = 'application/octet-stream'
            if content:
                retFile['content'] = fileData.content.decode('utf8')
        return retFile

    def postRequest(self, path, action=False, params=False):
        url = self.baseURL + path
        if action:
            data = {'operation':action}
        if params:
            for parSet in params:
                data[parSet[0]] = parSet[1]
        res = requests.post(url, headers = self.authHeader, data=data)
        return res

    def operateOnFile(self,filePath, action, params=False):
        res = self.postRequest('/file/?p={0}'.format(filePath), action, params)
        # url = self.baseURL + '/file/?p={0}'.format(filePath)
        # data = {'operation':action}
        # if params:
        #     for parSet in params:
        #         data[parSet[0]] = parSet[1]
        # res = requests.post(url, headers = self.authHeader, data=data)
        return res

    def operateOnDir(self,dirPath, action, params=False):
        res = self.postRequest('/dir/?p={0}'.format(dirPath), action, params)
        # url = self.baseURL + '/dir/?p={0}'.format(dirPath)
        # data = {'operation':action}
        # if params:
        #     for parSet in params:
        #         data[parSet[0]] = parSet[1]
        # res = requests.post(url, headers = self.authHeader, data=data)
        return res

    def deleteObject(self, path, type):
        if path == "/" or path == "":
            raise web.HTTPError(400,u'Cannot delete root folder.')
        if type == 'dir':
            url = self.baseURL + '/dir/?p={0}'.format(path)
        elif type == 'file':
            url = self.baseURL + '/file/?p={0}'.format(path)
        res = requests.delete(url, headers = self.authHeader)
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
        try:
            objects = path.split('/')
        except:
            try:
                objects = path['Referer'].split('/')
            except:
                raise ValueError("Cannot understand path: {0}".format(path))
        obj = objects[-1]
        if obj and obj.startswith('.'):
            return True
        elif obj:
            return False
        else:
            return False
            #raise ValueError('Cannot find object: {0}'.format(path))

    def file_exists(self, path):
        res = self.makeRequest('/file/history/?p={0}'.format(path))
        if res.status_code == 404:
            return False
        elif res.status_code == 200:
            return True

    def get(self, path, content=True, type=None, format=None):
        if not type:
            try:
                fileTrue = path.split('/')[-1].split('.')[1]
            except:
                fileTrue = ''
            if fileTrue:
                try:
                    ret =  self.getFileModel(path, content)
                except:
                    ret =  self.getDirModel(path, content)
            else:
                try:
                    ret =  self.getDirModel(path, content)
                except:
                    ret =  self.getFileModel(path, content)
        else:
            if type == "directory":
                ret =  self.getDirModel(path, content)
            elif type == "notebook" or type == "file":
                ret =  self.getFileModel(path, content)
        return ret

    def save(self, model, path=""):
        path = path.strip("/")

        if "type" not in model:
            raise web.HTTPError(400, u'No file type provided.')
        if 'content' not in model and model['type'] != 'directory':
            raise web.HTTPError(400, u'No file content provided.')

        self.log.debug("Saving %s", path)

        type = model['type']

        filename = path.split('/')[-1]
        filepath = '/'.join(path.split('/')[:-1])

        try:
            if model['type'] == "directory":
                self.operateOnDir('/' + path,'mkdir')
            elif model['type'] == "notebook":
                if not self.file_exists('/' + path):
                    self.operateOnFile('/' + path, 'create')
                else:
                    upload_link = self.makeRequest('/upload-link/').json()
                    res = self.postRequest(upload_link,
                        data={'filename':filename, 'parent_dir': filepath},
                        files={'file': nbformat.from_dict(model['content'])})
                    self.log.debug('{0}:{1}'.format(res.status_code,res.text))
                    #self.operateOnFile('/' + path, 'rename', [['newname', path.split('/')[-1] + '_old']])
            elif model['type'] == 'file':
                if not self.file_exists('/' + path):
                    self.operateOnFile('/' + path, 'create')
                else:
                    self.operateOnFile('/' + path, 'rename',  [['newname',  + '_old']])
        except web.HTTPError:
            raise
        except Exception as e:
            self.log.error(u'Error while saving file: %s %s', path, e, exc_info=True)
            raise web.HTTPError(500, u'Unexpected error while saving file: %s %s' % (path, e))

        validation_message = None
        if model['type'] == 'notebook':
            self.validate_notebook_model(model)
            validation_message = model.get('message', None)

        model = self.get(path, content=False, type=type)

        if validation_message:
            model['message'] = validation_message

        model['format'] = None

        return model

    def delete_file(self, path):
        pass

    def rename_file(self, old_path, new_path):
        if new_path == old_path:
            return
        if self.file_exists(new_path):
            raise web.HTTPError(409, 'File aready exists: {0}'.format(new_path))

        new_filename = new_path.split('/')[-1]

        res = self.operateOnFile(old_path, 'rename', [['newname', new_path]])

        if res.status_code in [301, 404]:
            return
        else:
            raise web.HTTPError(500, 'Operation failed, returned {0}'.format(res.status_code))

    def info_string(self):
        return "Serving notebooks from seafile library {0}, id {1}".format(self.libraryName, self.libraryID)

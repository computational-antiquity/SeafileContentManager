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
    A replacement ContentsManager for Jupyter Notebooks to use Seafiles WebAPI.
    Assumes three env variables set:

        SEAFILE_ACCESS_TOKEN: see https://manual.seafile.com/develop/web_api.html#quick-start
        SEAFILE_URL: e.g. https://sub.domain.com
        SEAFILE_LIBRARY: Library name, numerical ID is determined automatically for API calls

    """
    def __init__(self, *args, **kwargs ):
        # Seafile URL
        self.seafileURL = os.environ.get('SEAFILE_URL', '')
        if self.seafileURL != '':
            pass
        else:
            raise ValueError("Please set the SEAFILE_URL environment variable")
        # Access Token
        token = os.environ.get('SEAFILE_ACCESS_TOKEN','')
        if token != '':
            pass
        else:
            raise ValueError("Please set the SEAFILE_ACCESS_TOKEN environment variable")
        self.authHeader = {"Authorization":"Token {0}".format(token)}
        # check Authorization
        res = requests.get(self.seafileURL + '/api2/auth/ping/', headers = self.authHeader)
        assert res.text == '"pong"', 'Wrong token {0}, cannot access API at {1}.'.format(token, self.seafileURL + '/api2')
        # Destination library
        libraryName = os.environ.get('SEAFILE_LIBRARY', '')
        if libraryName != '':
            pass
        else:
            raise ValueError("Please set the SEAFILE_LIBRARY environment variable")
        resLib = requests.get(self.seafileURL + '/api2/repos/', headers = self.authHeader)
        idList = [x['id'] for x in resLib.json() if x['name'] == libraryName]
        # check if idList has one element = library ID
        assert 0 < len(idList) < 2, 'Cannot find specified library: {0}'.format(libraryName)
        # general information of seafile instance, not used yet
        self.serverInfo = requests.get(self.seafileURL + '/api2/server-info').json()
        # basic settings
        self.libraryID = idList[0]
        self.libraryName = libraryName

    def baseURL(self, apiVersion='/api2'):
        # allows to use both API versions
        return self.seafileURL + apiVersion +  '/repos/{0}'.format(self.libraryID)

    def makeRequest(self, apiPath, apiVersion='/api2'):
        # general GET requests form
        url = self.baseURL(apiVersion) + apiPath
        res = requests.get(url, headers = self.authHeader)
        return res

    def postRequest(self, path, apiVersion="/api2", action=False, params=False):
        # general POST request form, allows parameters, and special 'actions', e.g
        # delete, rename ...
        url = self.baseURL(apiVersion) + path
        data = {}
        if action:
            data = {'operation':action}
        if params:
            for parSet in params:
                data[parSet[0]] = parSet[1]
        if data != {}:
            res = requests.post(url, headers = self.authHeader, data=data)
        else:
            res = requests.post(url, headers = self.authHeader)
        return res

    def operateOnFile(self,filePath, action, params=False):
        # wrapper for file operations
        res = self.postRequest(path='/file/?p={0}'.format(filePath), action=action, params=params)
        return res

    def operateOnDir(self,dirPath, action, params=False):
        # wrapper for dir operations
        res = self.postRequest(path='/dir/?p={0}'.format(dirPath), action=action, params=params)
        return res

    def getDirModel(self, path, content=True):
        # return dir model with folder content as models without content
        files = self.makeRequest('/dir/?p={0}'.format(path)).json()
        dirDetail = self.makeRequest('/dir/detail/?path={0}'.format(path),apiVersion='/api/v2.1').json()
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
        retDir = {
            'content': fileList, 'format': 'json', 'mimetype': None,
            'type':'directory','name':dirDetail['name'],'writable':True,
            'last_modified':datetime.datetime.now(), 'path':path,
            'created': datetime.datetime.fromtimestamp(dirDetail['mtime']),
            'size': dirDetail['size']
            }
        return retDir

    def getFileModel(self, filePath, content = True):
        # return file model
        file = self.makeRequest('/file/detail/?p={0}'.format(filePath)).json()

        retFile = {}

        retFile['path'] = filePath.lstrip('/')

        try:
            fileType = file['name'].split('.')[-1]
        except:
            fileType = ''

        retFile['type'] = 'file'
        try:
            retFile['name'] = file['name']
        except:
            retFile['name'] = ''
        try:
            timestamp = ''.join(file['upload_time'].rsplit(':', 1))
            retFile['created'] = datetime.datetime.strptime(timestamp,'%Y-%m-%dT%H:%M:%S%z')
        except:
            retFile['created'] = datetime.datetime.now()
        try:
            retFile['last_modified'] = datetime.datetime.fromtimestamp(file['mtime'])
        except:
            retFile['last_modified'] = datetime.datetime.now()
        try:
            if file['permission'] == 'rw':
                retFile['writable'] = True
            else:
                retFile['writable'] = False
        except:
            retFile['writable'] = True

        if fileType in ['txt','md']:
            retFile['format'] = 'text'
            retFile['mimetype'] = 'text/plain'
            if content:
                fileData = ""
                dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
                if not "error_msg" in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = fileDataReq.text
                    except:
                        raise web.HTTPError(404, 'Can not get data content: {0}.\nGot response {1}.' .format(filePath, fileDataReq.text))
                retFile['content'] = fileData # fileData.content.decode('utf8')
        elif fileType == 'ipynb':
            retFile['type'] = 'notebook'
            retFile['format'] = 'json'
            retFile['mimetype'] = None
            if content:
                fileData = ""
                dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
                if not "error_msg" in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = nbformat.from_dict(fileDataReq.json())
                    except:
                        raise web.HTTPError(404, 'Can not get data content: {0}.\nGot response {1}.' .format(filePath, fileDataReq.content))
                # cont = nbformat.from_dict(fileData.json())
                retFile['content'] = fileData # cont
        else:
            retFile['format'] = 'base64'
            retFile['mimetype'] = 'application/octet-stream'
            if content:
                fileData = ""
                dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
                if not "error_msg" in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = fileDataReq.content
                    except:
                        raise web.HTTPError(404, 'Can not get data content: {0}.\nGot response {1}.' .format(filePath, fileDataReq.text))
                retFile['content'] = fileData # .content.decode('utf8')

        return retFile

    def dir_exists(self, path):
        # check if dir exists, use status code from Seafile API
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
         ## Root folder should never be hidden...
        if self.allow_hidden:
            return False
        elif path == "/":
            return False
        elif path == "":
            return False
        try:
            objects = path.split('/')
        except:
            try:
                objects = path['Referer'].split('/')
            except:
                raise web.HTTPError(500, u"Cannot understand path: %s" % path)
        obj = objects[-1]
        if obj and obj.startswith('.'):
            return True
        elif obj:
            return False
        else:
            return False

    def file_exists(self, path):
        # check if file exists, uses status code of Seafile API
        res = self.makeRequest('/file/history/?p={0}'.format(path))
        if res.status_code == 404:
            return False
        elif res.status_code == 200:
            return True
        elif res.status_code == 400:
            raise web.HTTPError(400, u'Invalid path')

    def get(self, path, content=True, type=None, format=None):
        # get model of folder or file
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

    def fileUpload(self, filename, filepath, modelContent, replace=True):
        # wrapper for upload requests, first generates an upload link, then
        # posts file details and model content
        upload_link = self.makeRequest('/upload-link/').json()
        if replace:
            replace = 1
        else:
            replace = 0
        res = requests.post(upload_link,
            data={
                'filename':filename,
                'parent_dir': filepath,
                'replace': replace
            },
            files={'file':(filename,modelContent)})
        self.log.debug('{0}:{1}'.format(res.status_code,res.text))
        return res

    def save(self, model, path=""):
        # save needs upload calls to Seafile API
        path = path.strip("/")

        if "type" not in model:
            raise web.HTTPError(400, u'No file type provided.')
        if 'content' not in model and model['type'] != 'directory':
            raise web.HTTPError(400, u'No file content provided.')

        self.log.debug("Saving %s", path)

        type = model['type']

        filename = path.split('/')[-1]
        filepath = '/'.join(path.split('/')[:-1]) + '/'

        try:
            if model['type'] == "directory":
                self.operateOnDir('/' + path,'mkdir')
            elif model['type'] == "notebook":
                if not self.file_exists('/' + path):
                    self.fileUpload(filename, filepath, json.dumps(nbformat.v4.new_notebook()), replace=False)
                else:
                    self.fileUpload(filename, filepath, json.dumps(model['content']))
            elif model['type'] == 'file':
                if not self.file_exists('/' + path):
                    self.operateOnFile('/' + path, 'create')
                else:
                    self.fileUpload(filename, filepath, str.encode(model['content']))
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
        model['content'] = None
        return model

    def deleteObject(self, path, type):
        # wrapper for delete operations, generates DELETE requests to Seafile API
        if path == "/" or path == "":
            raise web.HTTPError(400,u'Cannot delete root folder.')
        if type == 'dir':
            url = self.baseURL() + '/dir/?p={0}'.format(path)
        elif type == 'file':
            url = self.baseURL() + '/file/?p={0}'.format(path)
        res = requests.delete(url, headers = self.authHeader)
        return res

    def delete_file(self, path):
        # delete file or folder
        try:
            fileTrue = path.split('/')[-1].split('.')[1]
        except:
            fileTrue = ''
        if fileTrue:
            try:
                ret =  self.deleteObject(path, type='file')
            except:
                raise web.HTTPError(u"Cannot delete file at %s" % path)
        else:
            try:
                ret =  self.deleteObject(path, type='dir')
            except:
                raise web.HTTPError(u"Cannot delete folder at %s" % path)
        return

    def rename_file(self, old_path, new_path):
        # rename file or folder 
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

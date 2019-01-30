from datetime import datetime
import os
import sys
import requests
import json
import nbformat

from tornado import web
from traitlets import Any, Unicode, Bool, TraitError, observe, default, validate

from notebook.services.contents.manager import ContentsManager

from .seacheckpoints import SeafileCheckpoints
from .seafilemixin import getConnection

class SeafileContentManager(ContentsManager):
    """
    A replacement ContentsManager for Jupyter Notebooks to use Seafiles WebAPI.
    Assumes three env variables set:

        SEAFILE_ACCESS_TOKEN: see https://manual.seafile.com/develop/web_api.html#quick-start
        SEAFILE_URL: e.g. https://sub.domain.com
        SEAFILE_LIBRARY: Library name, numerical ID is determined automatically for API calls

    """
    @default('checkpoints_class')
    def _checkpoints_class_default(self):
        return SeafileCheckpoints

    def __init__(self, *args, **kwargs ):
        retVals = getConnection()

        self.seafileURL=retVals[0]
        self.authHeader=retVals[1]
        self.libraryID=retVals[2]
        self.libraryName=retVals[3]
        self.serverInfo=retVals[4]

    def baseURL(self, apiVersion='/api2'):
        # allows to use both API versions
        return self.seafileURL + apiVersion +  '/repos/{0}'.format(self.libraryID)

    def makeRequest(self, apiPath, apiVersion='/api2'):
        # general GET requests form
        url = self.baseURL(apiVersion) + apiPath
        res = requests.get(url, headers = self.authHeader)
        return res

    def postRequest(self, apiPath, apiVersion="/api2", action=False, params=False):
        # general POST request form, allows parameters, and special 'actions', e.g
        # delete, rename ...
        url = self.baseURL(apiVersion) + apiPath
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

    def operateOnFile(self, filePath, action, apiVersion="/api2", params=False):
        # wrapper for file operations
        res = self.postRequest(apiPath='/file/?p={0}'.format(filePath), action=action, params=params)
        return res

    def operateOnDir(self, dirPath, action, apiVersion="/api2", params=False):
        # wrapper for dir operations
        res = self.postRequest(apiPath='/dir/?p={0}'.format(dirPath), action=action, params=params)
        return res

    def getDirModel(self, path, content=True, format=True):
        # return dir model with folder content as models without content
        files = self.makeRequest('/dir/?p={0}'.format(path)).json()
        dirDetail = self.makeRequest('/dir/detail/?path={0}'.format(path),apiVersion='/api/v2.1').json()
        if content:
            dirFormat = 'json'
            try:
                fileList = []
                for fileDict in files:
                    res = {}
                    res['last_modified'] = datetime.fromtimestamp(fileDict['mtime'])
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
            dirFormat = None
        try:
            dirname = dirDetail['name']
        except:
            dirname = None
        try:
            dirdate = dirDetail['mtime']
        except:
            dirdate = datetime.now()
        try:
            dirsize = dirDetail['size']
        except:
            dirsize = None

        retDir = {
            'content': fileList, 'format': dirFormat, 'mimetype': None,
            'type':'directory','name': dirname,'writable':True,
            'last_modified':datetime.now(), 'path':path,
            'created': dirdate,
            'size': dirsize
            }
        return retDir

    def getFileModel(self, filePath, content=True, format=None):
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
            retFile['created'] = datetime.strptime(timestamp,'%Y-%m-%dT%H:%M:%S%z')
        except:
            retFile['created'] = datetime.now()
        try:
            retFile['last_modified'] = datetime.fromtimestamp(file['mtime'])
        except:
            retFile['last_modified'] = datetime.now()
        try:
            if file['permission'] == 'rw':
                retFile['writable'] = True
            else:
                retFile['writable'] = False
        except:
            retFile['writable'] = True

        if fileType in ['txt','md']:
            retFile['format'] = None
            retFile['mimetype'] = 'text/plain'
            if content:
                retFile['format'] = 'text'
                fileData = ""
                dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
                if not "error_msg" in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = fileDataReq.text
                    except:
                        raise web.HTTPError(404, 'Can not get data content: {0}.\nGot response {1}.' .format(filePath, fileDataReq.text))
                retFile['content'] = fileData
            else:
                retFile['content'] = None
        elif fileType == 'ipynb':
            retFile['type'] = 'notebook'
            retFile['format'] = None
            retFile['mimetype'] = None
            if content:
                retFile['format'] = 'json'
                fileData = ""
                dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
                if not "error_msg" in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = nbformat.from_dict(fileDataReq.json())
                    except:
                        raise web.HTTPError(404, 'Can not get data content: {0}.\nGot response {1}.' .format(filePath, fileDataReq.content))
                retFile['content'] = fileData
            else:
                retFile['content'] = None
        else:
            retFile['format'] = None
            retFile['mimetype'] = 'application/octet-stream'
            if content:
                retFile['format'] = 'base64'
                fileData = ""
                dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
                if not "error_msg" in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = fileDataReq.content
                    except:
                        raise web.HTTPError(404, 'Can not get data content: {0}.\nGot response {1}.' .format(filePath, fileDataReq.text))
                retFile['content'] = fileData
            else:
                retFile['content'] = None
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
        self.log.debug('Current get call for type {0} on {1} with format {2} and content {3}'.format(type, path,format,content))
        if not type:
            try:
                fileTrue = path.split('/')[-1].split('.')[1]
            except:
                fileTrue = ''
            if fileTrue:
                try:
                    ret =  self.getFileModel(path, content)
                except:
                    ret =  self.getDirModel(path, content, format)
            else:
                try:
                    ret =  self.getDirModel(path, content, format)
                except:
                    ret =  self.getFileModel(path, content)
        else:
            if type == "directory":
                ret =  self.getDirModel(path, content, format)
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
        self.log.debug("Got model: {0}".format(model))
        type = model['type']

        filename = path.split('/')[-1]
        filepath = '/'.join(path.split('/')[:-1]) + '/'

        try:
            if model['type'] == "directory":
                self.operateOnDir('/' + path,'mkdir')
            elif model['type'] == "notebook":
                if not self.file_exists('/' + path):
                    if model['content']=='':
                        self.fileUpload(filename, filepath, json.dumps(nbformat.v4.new_notebook()), replace=False)
                    else:
                        self.fileUpload(filename, filepath, json.dumps(model['content']))
                else:
                    self.fileUpload(filename, filepath, json.dumps(model['content']))
            elif model['type'] == 'file':
                if not self.file_exists('/' + path):
                    if model['content']=='':
                        self.operateOnFile(filePath='/' + path, action='create')
                    else:
                        self.fileUpload(filename, filepath, str.encode(model['content']))
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
                raise web.HTTPError(404, u"Cannot delete file at %s" % path)
        else:
            try:
                ret =  self.deleteObject(path, type='dir')
            except:
                raise web.HTTPError(404, u"Cannot delete folder at %s" % path)
        return

    def rename_file(self, old_path, new_path):
        # rename file or folder
        if new_path == old_path:
            return
        if self.file_exists(new_path):
            raise web.HTTPError(409, 'File aready exists: {0}'.format(new_path))

        new_filename = new_path.split('/')[-1]
        res = self.operateOnFile(filePath='/' + old_path, action='rename', params=[['newname', new_filename]])

        if res.status_code in [200, 301, 404]:
            return
        else:
            raise web.HTTPError(500, 'Operation failed, returned {0}'.format(res.status_code))

    def info_string(self):
        return "Serving notebooks from seafile library {0}, id {1}".format(self.libraryName, self.libraryID)

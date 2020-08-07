#! python3
# -*- coding: utf-8 -*-

from datetime import datetime
import json
import requests
import nbformat

from tornado import web
from traitlets import default

from notebook.services.contents.manager import ContentsManager

from .seacheckpoints import SeafileCheckpoints
from .seafilemixin import getConnection


class SeafileContentManager(ContentsManager):
    """Replacement content manager.

    A replacement ContentsManager for Jupyter Notebooks to use Seafiles WebAPI.
    Assumes three env variables set:

        SEAFILE_ACCESS_TOKEN:
            see https://manual.seafile.com/develop/web_api.html#quick-start
        SEAFILE_URL:
            e.g. https://sub.domain.com
        SEAFILE_LIBRARY:
            Library name, numerical ID is determined automatically for API calls
    """
    @default('checkpoints_class')
    def _checkpoints_class_default(self):
        return SeafileCheckpoints

    def __init__(self, *args, **kwargs):
        retVals = getConnection()

        self.seafileURL = retVals[0]
        self.authHeader = retVals[1]
        self.libraryID = retVals[2]
        self.libraryName = retVals[3]
        self.seafileMainVs = retVals[4]

    def baseURL(self, apiVersion='/api2'):
        """Allow to use both API versions."""
        if self.seafileMainVs < 7:
            return self.seafileURL + apiVersion + '/repos/{0}'.format(self.libraryID)
        else:
            return self.seafileURL + '/api/v2.1/via-repo-token'

    def makeRequest(self, apiPath, apiVersion='/api2'):
        """Create GET requests form."""
        url = self.baseURL(apiVersion) + apiPath
        res = requests.get(url, headers=self.authHeader)
        res.encoding = 'utf-8'
        return res

    def postRequest(self, apiPath, apiVersion="/api2", action=False, params=False):
        """Generate post requests.

        General POST request form, allows parameters and special 'actions', e.g
        delete, rename ..
        """
        url = self.baseURL(apiVersion) + apiPath
        data = {}
        if action:
            data = {'operation': action}
        if params:
            for parSet in params:
                data[parSet[0]] = parSet[1]
        if data != {}:
            res = requests.post(url, headers=self.authHeader, data=data)
        else:
            res = requests.post(url, headers=self.authHeader)
        res.encoding = res.apparent_encoding
        return res

    def operateOnFile(self, filePath, action, apiVersion="/api2", params=False):
        """Wrap file operations."""
        res = self.postRequest(
            apiPath='/file/?p={0}'.format(filePath),
            action=action,
            params=params
        )
        return res

    def operateOnDir(self, dirPath, action, apiVersion="/api2", params=False):
        """Wrap dir operations."""
        res = self.postRequest(
            apiPath='/dir/?p={0}'.format(dirPath), action=action, params=params
            )
        return res

    def convertDataModel(self, path, inModel):
        res = {}
        res['last_modified'] = datetime.fromtimestamp(
            inModel['mtime']
            )
        res['name'] = inModel['name']
        filepath = path + '/' + inModel['name']
        res['path'] = filepath.lstrip('/')
        if inModel['permission'] == 'rw':
            res['writeable'] = True
        else:
            res['writeable'] = False
        if inModel['type'] == 'file':
            res['size'] = inModel['size']
            try:
                fileType = res['name'].split('.')[1]
                if fileType == 'ipynb':
                    res['type'] = 'notebook'
                else:
                    res['type'] = 'file'
            except:
                res['type'] = 'file'
        elif inModel['type'] == 'dir':
            res['type'] = 'directory'
        res['format'] = None
        res['mimetype'] = None
        res['content'] = None
        return res


    def getDirModel(self, path, content=True):  # , format=True):
        """Return dir model with folder content as models without content."""
        if self.seafileMainVs >= 7:
            files =  self.makeRequest('/dir/?p={0}'.format(path)).json()['dirent_list']
            dirDetail = {}
        else:
            files = self.makeRequest('/dir/?p={0}'.format(path)).json()
            dirDetail = self.makeRequest(
                '/dir/detail/?path={0}'.format(path),
                apiVersion='/api/v2.1'
                ).json()
        if content:
            dirFormat = 'json'
            try:
                fileList = []
                for fileDict in files:
                    res = self.convertDataModel(path, fileDict)
                    fileList.append(res)
            # Empty folder have no content, list nothing...
            except:
                fileList = None
        else:
            fileList = None
            dirFormat = None
        try:
            dirname = dirDetail['name']
        except:
            # feature JupyterLab
            # in JupyterLab validateContentsModel requires keys to be either string or object, see
            # https://github.com/jupyterlab/jupyterlab/blob/1aff4190084fd5993d3f7e3ae10b467264df1cd0/packages/services/src/contents/validate.ts#L36
            dirname = ''
        try:
            dirdate = dirDetail['mtime']
        except:
            dirdate = datetime.now()
        try:
            dirsize = dirDetail['size']
        except:
            # feature JupyterLab
            dirsize = ''

        retDir = {
            'content': fileList, 'format': dirFormat, 'mimetype': None,
            'type': 'directory', 'name': dirname, 'writable': True,
            'last_modified': datetime.now(), 'path': path,
            'created': dirdate,
            'size': dirsize
            }
        return retDir

    def getFileModel(self, filePath, content=True):
        """Return file model."""

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
            retFile['created'] = datetime.strptime(
                timestamp, '%Y-%m-%dT%H:%M:%S%z'
                )
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

        if fileType in ['txt', 'md']:
            retFile['format'] = None
            retFile['mimetype'] = 'text/plain'
            if content:
                retFile['format'] = 'text'
                fileData = ""
                dlLink = self.makeRequest('/file/?p={0}'.format(filePath))
                if "error_msg" not in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    fileDataReq.encoding = 'utf-8'
                    try:
                        fileData = fileDataReq.text
                    except:
                        raise web.HTTPError(
                            404,
                            'Can not get data content: {0}.\n\
                            Got response {1}.'.format(
                                filePath, fileDataReq.text)
                            )
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
                if "error_msg" not in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = nbformat.from_dict(fileDataReq.json())
                    except:
                        raise web.HTTPError(
                            404,
                            'Can not get data content: {0}.\n\
                            Got response {1}.'.format(
                                filePath, fileDataReq.content)
                        )
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
                if "error_msg" not in dlLink.json():
                    fileDataReq = requests.get(dlLink.json())
                    try:
                        fileData = fileDataReq.content
                    except:
                        raise web.HTTPError(
                            404,
                            'Can not get data content: {0}.\n\
                            Got response {1}.'.format(
                                filePath, fileDataReq.text)
                            )
                retFile['content'] = fileData
            else:
                retFile['content'] = None
        return retFile

    def dir_exists(self, path):
        """Check if dir exists, use status code from Seafile API."""
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
        """Check for hidden folder. Root folder should never be hidden."""
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
        """Check if file exists, uses status code of Seafile API."""
        res = self.makeRequest('/file/history/?p={0}'.format(path))
        if res.status_code == 404:
            return False
        elif res.status_code == 200:
            return True
        elif res.status_code == 400:
            raise web.HTTPError(400, u'Invalid path')

    def get(self, path, content=True, type=None, format=None):
        """Get model of folder or file."""
        self.log.debug(
            'Current GET for type {0} on {1} \
            with format {2} and content {3}'.format(
                type, path, format, content)
                )
        if not type:
            try:
                fileTrue = path.split('/')[-1].split('.')[1]
            except:
                fileTrue = ''
            if fileTrue:
                try:
                    ret = self.getFileModel(path, content)
                except:
                    ret = self.getDirModel(path, content)
            else:
                try:
                    ret = self.getDirModel(path, content)
                except:
                    ret = self.getFileModel(path, content)
        else:
            if type == "directory":
                ret = self.getDirModel(path, content)
            elif type in ("notebook", "file"):
                ret = self.getFileModel(path, content)
        return ret

    def fileUpload(self, filename, filepath, modelContent, replace=True):
        """Wrap uploads.
        Wrapper for upload requests, first generates an upload link, then
        posts file details and model content.
        """
        upload_link = self.makeRequest('/upload-link/').json()
        if replace:
            replace = 1
        else:
            replace = 0
        res = requests.post(upload_link,
                            data={
                                'filename': filename,
                                'parent_dir': filepath,
                                'replace': replace
                                },
                            files={'file': (filename, modelContent)}
                            )
        self.log.debug('{0}:{1}'.format(res.status_code, res.text))
        return res

    def save(self, model, path=""):
        """Save needs upload calls to Seafile API."""
        path = path.strip("/")

        if "type" not in model:
            raise web.HTTPError(400, u'No file type provided.')
        if 'content' not in model and model['type'] != 'directory':
            raise web.HTTPError(400, u'No file content provided.')

        self.log.debug("Saving %s", path)
        # self.log.debug("Got model: {0}".format(model))
        type_ = model['type']

        filename = path.split('/')[-1]
        filepath = '/'.join(path.split('/')[:-1]) + '/'

        try:
            if model['type'] == "directory":
                self.operateOnDir('/' + path, 'mkdir')
            elif model['type'] == "notebook":
                if not self.file_exists('/' + path):
                    if model['content'] == '':
                        self.fileUpload(
                            filename, filepath,
                            json.dumps(nbformat.v4.new_notebook()),
                            replace=False
                            )
                    else:
                        self.fileUpload(
                            filename, filepath, json.dumps(model['content'])
                            )
                else:
                    self.fileUpload(
                        filename, filepath, json.dumps(model['content'])
                        )
            elif model['type'] == 'file':
                if not self.file_exists('/' + path):
                    if model['content'] == '':
                        self.operateOnFile(
                            filePath='/' + path, action='create'
                            )
                    else:
                        # JupyterLab feature
                        self.fileUpload(filename, filepath, model['content'])
                else:
                    self.fileUpload(filename, filepath, model['content'])
        except web.HTTPError:
            raise
        except Exception as e:
            self.log.error(
                u'Error while saving file: %s %s', path, e, exc_info=True
                )
            raise web.HTTPError(
                500, u'Unexpected error while saving file: %s %s' % (path, e)
                )
        validation_message = None
        if model['type'] == 'notebook':
            self.validate_notebook_model(model)
            validation_message = model.get('message', None)
        model = self.get(path, content=False, type=type_)
        if validation_message:
            model['message'] = validation_message
        model['format'] = None
        model['content'] = None
        return model

    def deleteObject(self, path, type_):
        """Wrap delete operations, generates DELETE requests."""
        if path in ("/", ""):
            raise web.HTTPError(400, u'Cannot delete root folder.')
        if type_ == 'dir':
            url = self.baseURL() + '/dir/?p={0}'.format(path)
        elif type_ == 'file':
            url = self.baseURL() + '/file/?p={0}'.format(path)
        res = requests.delete(url, headers=self.authHeader)
        return res

    def delete_file(self, path):
        """Delete file or folder."""
        try:
            fileTrue = path.split('/')[-1].split('.')[1]
        except:
            fileTrue = ''
        if fileTrue:
            try:
                self.deleteObject(path, type_='file')
            except:
                raise web.HTTPError(404, u"Cannot delete file at %s" % path)
        else:
            try:
                self.deleteObject(path, type_='dir')
            except:
                raise web.HTTPError(404, u"Cannot delete folder at %s" % path)

    def rename_file(self, old_path, new_path):
        """Rename file or folder."""
        if new_path == old_path:
            return
        if self.file_exists(new_path):
            raise web.HTTPError(
                409, 'File aready exists: {0}'.format(new_path)
                )

        new_filename = new_path.split('/')[-1]
        old_filename = old_path.split('/')[-1]

        new_filepath = '/'.join(new_path.split('/')[:-1])
        old_filepath = '/'.join(old_path.split('/')[:-1])

        if new_filename != old_filename:
            res = self.operateOnFile(
                filePath='/' + old_path,
                action='rename',
                params=[['newname', new_filename]]
                )
        elif new_filepath != old_filepath and new_filename == old_filename:
            res = self.operateOnFile(
                filePath='/' + old_path,
                action='move',
                params=[
                    ['dst_dir', new_filepath], ['dst_repo', self.libraryID]
                    ]
                )
        else:
            pass

        if res.status_code in [200, 301, 404]:
            return
        self.log.error('Error saving file {0} in path {1}'.format(
            new_filename, new_path
            ))
        raise web.HTTPError(500, 'Operation failed, returned {0}'.format(
            res.status_code
            ))

    def info_string(self):
        """Return info."""
        return "Serving notebooks from seafile library {0}, id {1}".format(
            self.libraryName, self.libraryID
            )

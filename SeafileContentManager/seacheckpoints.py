#! python3
# -*- coding: utf-8 -*-

from datetime import datetime
import os
import sys
import requests
import json
import nbformat

from tornado import web

from notebook.services.contents.checkpoints import Checkpoints, GenericCheckpointsMixin

from .seafilemixin import getConnection

class SeafileCheckpoints(GenericCheckpointsMixin, Checkpoints):
    """
    A replacement Checkpoints Manager for Jupyter Notebooks to use the SeaFile
    Commit History.
    Assumes three env variables set:

        SEAFILE_ACCESS_TOKEN: see https://manual.seafile.com/develop/web_api.html#quick-start
        SEAFILE_URL: e.g. https://sub.domain.com
        SEAFILE_LIBRARY: Library name, numerical ID is determined automatically for API calls

    """
    def __init__(self, *args, **kwargs):
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

    def getRevision(self, checkpoint_id, path):
        reqResult = self.makeRequest('/file/revision/?p={0}&commit_id={1}'.format(path, checkpoint_id))
        if reqResult.status_code in [400,404]:
            raise web.HTTPError(reqResult.status_code, u"Cannot find checkpoint %s for path %s" % (checkpoint_id, path))
        fileData = requests.get(reqResult.json())
        fileData.encoding = fileData.apparent_encoding
        return fileData

    # DUMMY METHODS: We use Seafiles internal commit history and have no active
    # checkpointing

    def create_file_checkpoint(self, content, format, path):
        """ -> checkpoint model"""
        ret = {
            'id':'autocheckpointing',
            'last_modified':datetime.now()
        }
        return ret

    def create_notebook_checkpoint(self, nb, path):
        """ -> checkpoint model"""
        ret = {
            'id':'autocheckpointing',
            'last_modified':datetime.now()
        }
        return ret

    def delete_checkpoint(self, checkpoint_id, path):
        """deletes a checkpoint for a file"""
        pass

    def rename_checkpoint(self, checkpoint_id, old_path, new_path):
        """renames checkpoint from old path to new path"""
        pass

    # Seafile Commit history as checkpoints

    def get_file_checkpoint(self, checkpoint_id, path):
        """ -> {'type': 'file', 'content': <str>, 'format': {'text', 'base64'}}"""
        data = self.getRevision(checkpoint_id, path)
        text = data.text
        ret = {'type': 'file', 'content': text, 'format': {'text', 'base64'}}
        return ret

    def get_notebook_checkpoint(self, checkpoint_id, path):
        """ -> {'type': 'notebook', 'content': <output of nbformat.read>}"""
        data = self.getRevision(checkpoint_id, path)
        nb = nbformat.from_dict(data.json())
        ret = {'type': 'notebook', 'content': nb}
        return ret

    def list_checkpoints(self, path):
        """returns a list of checkpoint models for a given file,
        default just does one per file
        """
        ret = []
        if not path.startswith('/'):
            path = '/' + path
        reqResult = self.makeRequest('/file/history/?path={0}'.format(path),apiVersion='/api/v2.1').json()
        try:
            checkpoints = reqResult['data']
        except:
            self.log.debug('Cannot obtain checkpoints for {0}'.format(path))
            return []
        for elem in checkpoints:
            timestamp = ''.join(elem['ctime'].rsplit(':', 1))
            ret.append(
                {
                    'id':elem['commit_id'],
                    'last_modified': datetime.strptime(timestamp,'%Y-%m-%dT%H:%M:%S%z')
                }
            )
        return ret

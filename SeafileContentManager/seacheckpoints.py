import datetime
import os
import sys
import requests
import json
import nbformat

from tornado import web

from notebook.services.contents.checkpoints import Checkpoints, GenericCheckpointsMixin

from .seamanager import SeafileContentManager

class SeaCheckpoints(GenericCheckpointsMixin, Checkpoints, SeafileContentManager):
    """
    A replacement Checkpoints Manager for Jupyter Notebooks to use the SeaFile
    Commit History. 
    Assumes three env variables set:

        SEAFILE_ACCESS_TOKEN: see https://manual.seafile.com/develop/web_api.html#quick-start
        SEAFILE_URL: e.g. https://sub.domain.com
        SEAFILE_LIBRARY: Library name, numerical ID is determined automatically for API calls

    """
    def __init__(self):
        super(SeaCheckpoints, self).__init__()

    def getRevision(self, checkpoint_id, path):
        reqResult = self.makeRequest('file/revision/?p={0}\&commit_id={1}'.format(path, checkpoint_id))
        if reqResult.status_code in [400,404]:
            raise web.HTTPError(u"Cannot find checkpoint %s for path %s" % (checkpoint_id, path))
        return reqResult

    # DUMMY METHODS: We use Seafiles internal commit history and have no active
    # checkpointing

    def create_file_checkpoint(self, content, format, path):
        """ -> checkpoint model"""
        ret = {
            'id':'autocheckpointing',
            'last_modified':datetime.datetime.now()
        }
        return ret

    def create_notebook_checkpoint(self, nb, path):
        """ -> checkpoint model"""
        ret = {
            'id':'autocheckpointing',
            'last_modified':datetime.datetime.now()
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
        reqResult = self.makeRequest('/file/history/?path={0}'.format(path),apiVersion='/api/v2.1').json()
        try:
            checkpoints = reqResult['data']
        except:
            raise web.HTTPError(u'Cannot obtain checkpoints for %s' % path)
        for elem in checkpoints:
            ret.append(
                {
                    'id':elem['commit_id'],
                    'last_modified':datetime.datetime.fromtimestamp(elem['ctime'])
                }
            )
        return ret

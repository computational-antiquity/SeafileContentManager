from notebook.services.contents.checkpoints import Checkpoints, GenericCheckpointsMixin

class SeaCheckpoints(GenericCheckpointsMixin, Checkpoints):
    """requires the following methods:"""
    def create_file_checkpoint(self, content, format, path):
        """ -> checkpoint model"""
        return
    def create_notebook_checkpoint(self, nb, path):
        """ -> checkpoint model"""
        return
    def get_file_checkpoint(self, checkpoint_id, path):
        """ -> {'type': 'file', 'content': <str>, 'format': {'text', 'base64'}}"""
        return
    def get_notebook_checkpoint(self, checkpoint_id, path):
        """ -> {'type': 'notebook', 'content': <output of nbformat.read>}"""
        return
    def delete_checkpoint(self, checkpoint_id, path):
        """deletes a checkpoint for a file"""
        return
    def list_checkpoints(self, path):
        """returns a list of checkpoint models for a given file,
        default just does one per file
        """
        return []
    def rename_checkpoint(self, checkpoint_id, old_path, new_path):
        """renames checkpoint from old path to new path"""
        return

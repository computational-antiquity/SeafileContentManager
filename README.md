# SeafileContentManager
A custom ContentManger for Jupyter Notebooks based on [Seafiles WebAPI](https://manual.seafile.com/develop/web_api_v2.1.html) following the notes on [Custom ContentManagers](https://jupyter-notebook.readthedocs.io/en/stable/extending/contents.html#testing).

The ContentManger works for both Jupyter Notebook and Lab. Checkpoints for files, folders and notebooks are are based on the Seafile [Commit History](https://www.seafile.com/en/help/snapshot/). Thus, checkpoints are available for a predefined period of time ('retention period', e.g. 30 days, can also be infinite, see [here](https://www.seafile.com/en/help/history_setting/)).

Since for Python IO operations (e.g. `open('file.txt','r') as file`) the underlying file system is used, there is an additional
drop-in replacement for those operations

```python3
from SeafileContentManager import SeafileFS

fs = SeafileFS()

file = fs.open('/text.txt','r')

file.read()
```

Ideally, notebooks should be written with this replacement from the start. 

## Status
Currently under active development.

What works?
- In JupyterLab or Notebook GUI:
  - Folder view
  - Opening and saving notebooks
  - Opening and saving text files (.txt,.md)
  - Creating new folder, file or notebook
  - Download
  - Duplicate
  - Renaming
  - Moving files
- Using the SeafileFS drop-in replacement for io operations:
  - Opening files in all modes (r,a,w,x, or adding b, +)
  - Reading
  - Writing (not yet a+, a+b modes)
  - listdir
  - listdir_attrib (with file size, creation date, etc.)
  - mkdir


What does not work?
  - Drag and Drop Upload in JupyterLab
    - Files end up b64 encoded on the Seafile FS
  - Relative paths in the SeafileFS
    - All paths are taken from the root, i.e. the at startup selected SeaFile library

## Testing

To test the content manager, clone the repository, create a new virtual environment
```
virtualenv -p python3 env
```
in the cloned directory, activate it
```
source env/bin/activate
```
 and install the development version
```
pip install -U .
```

Export the following environment variables
- SEAFILE_URL: The url to access your SeaFile instance
- SEAFILE_ACCESS_TOKEN: Your access token
- SEAFILE_LIBRARY: The name of the library, where all

e.g. by having a file `env` in your testing folder (don't forget to add it to gitignore!)
with the following content
```bash
#!/bin/bash
export SEAFILE_URL=https://my.seafile.instance
export SEAFILE_LIBRARY=notebooks
export SEAFILE_ACCESS_TOKEN=12341234124124
```
and then sourcing the file (`source testing/env`) before running the command below.

### Jupyter Notebook

To start Jupyter notebook from the activated environment run
```
jupyter notebook \
  --NotebookApp.contents_manager_class=SeafileContentManager.SeafileContentManager \
  --ContentsManager.checkpoints_class=SeafileContentManager.SeafileCheckpoints \
  --debug
```
This should start Jupyter notebooks with the Seafile API
contents and checkpoints manager.  

### JupyterLab
To use the ContentManger with Jupyter Lab, create a settings file with the following content
```python
from SeafileContentManager import SeafileContentManager, SeafileCheckpoints
c = get_config()
c.NotebookApp.contents_manager_class = SeafileContentManager
c.ContentsManager.checkpoints_class = SeafileCheckpoints
```
and run
```
jupyter-lab --config /path/to/config/jupyter_notebook_config.py --debug
```

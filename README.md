# SeafileContentManager
A custom ContentManger for Jupyter Notebooks based on [Seafiles WebAPI](https://manual.seafile.com/develop/web_api_v2.1.html) following the notes on [Custom ContentManagers](https://jupyter-notebook.readthedocs.io/en/stable/extending/contents.html#testing).

## Status
Currently in active development.

What works?
- Folder view
- Opening and saving notebooks
- Opening and saving text files (.txt,.md)
- Creating new folder, file or notebook
- Download
- Duplicate
- Renaming

What is not working?
- Moving files: Most likely an error in the source path definition

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

To start Jupyter notebook from the activated environment run
```
jupyter notebook \
  --NotebookApp.contents_manager_class=SeafileContentManager.SeafileContentManager \
  --ContentsManager.checkpoints_class=SeafileContentManager.SeafileCheckpoints \
  --debug
```
This should start Jupyter notebooks with the Seafile API
contents and checkpoints manager.  

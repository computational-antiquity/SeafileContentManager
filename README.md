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

What is partly working?
- Duplicate creates new file with same name, without content.

What is not working?
- Renaming folders, files, or notebooks
- Moving files
- Checkpoints

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

To start Jupyter notebook from the activated environment run
```
jupyter notebook \
  --NotebookApp.contents_manager_class=SeafileContentManager.SeafileContentManager \
  --ContentsManager.checkpoints_class=SeafileContentManager.SeaCheckpoints \
  --debug
```
This should start Jupyter notebooks with the Seafile API
contents and checkpoints manager.  

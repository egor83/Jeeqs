Jeeqs
=====

Jeeqs is a collaborative problem solving and learning platform and is hosted at [`http://www.jeeqs.com`](http://www.jeeqs.com)


## Setting up Development environment 

* Download Python 2.7, and the latest [app engine SDK](https://developers.google.com/appengine/downloads) 
* Download and install Pycharm 
* Fork Jeeqs in github so you have a clone of Jeeqs under your username
* Add github plugin to Pycharm and download the project source into your local
* In Pycharm go to File -> Open Directory and open the root of the directory you downloaded (which should include src/ directory)
* Enable App Engine in Pycharm project settings as well as Jinja template language
* Add a Run configuration of type "App Engine Server" with python 2.7 as the interpreter and also add "--high_replication" to Additional Options field 
* You should be able to run Jeeqs locally using this run configuration.


## Importing data locally from cloud
In order to get the data, you would need to download the app's data first from Jeeqs on App Engine and then upload it to your local instance.
If you don't have permission to download the data, contact the project admin. The insturctions for downloading and uploading the data is in the header 
of "models.py" file. 

* downloading: appcfg.py download_data --url=http://jeeqsy.appspot.com/_ah/remote_api --filename=<SNAPSHOT_FILENAME> --application=s~jeeqsy
* uploading: appcfg.py upload_data --url=http://localhost:8080/_ah/remote_api --filename=<SNAPSHOT_FILENAME> --num_threads=1

## Troubleshooting

1) In case you encounter problems with local DB (like DB file not being created or its content not persisting when server is reloaded), with PyCharm giving you warnings about DB stubs, SQLite and MySQLdb, for instance:
> The rdbms API is not available because the MySQLdb library could not be loaded.

the following steps might help:

1.1) Install MySQLdb (from [Windows binaries](http://www.lfd.uci.edu/~gohlke/pythonlibs/#mysql-python) or as described in project's [Readme](https://sourceforge.net/projects/mysql-python/files/mysql-python/1.2.3/));

1.2) Use the following set of flags in project configuration, NB datastore_path should point to the file and not to the directory:
> --high_replication --datastore_path="<PATH_TO_DATASTORE_FILE>" --use_sqlite --default_partition=""

1.3) To cleanup the database, add --clear_datastore to the configuration above (you might want to save it as a separate project config);

1.4) Use the following command to upload data from snapshot to local DB:
> python <PATH_TO_GAE's_appcfg.py> upload_data --url=http://localhost:8080/_ah/remote_api --filename=<SNAPSHOT_FILENAME> --num_threads=1 <PATH_TO_JEEQ'S_src_DIRECTORY>

1.5) If PyCharm gives you the following error:
> google.appengine.api.datastore_errors.InternalError: unable to open database file

run PyCharm with admin rights (run as administrator on Windows, sudo on Linux&Mac);

1.6) (not sure if needed) I installed MySQL as well, but that might not be necessary.

2) If you cleanup the datastore and visit the local site's homepage before uploading the snapshot, you might start getting the following error after upload:
> UndefinedError: 'None' has no attribute 'challenge'

In that case just cleanup the datastore (see 1.3 above) and upload the data from snapshot (see 1.4 above) right after that.

## Code style
* The standard code style for python files in Jeeqs is [pep8](http://www.python.org/dev/peps/pep-0008/). 
* Install `pep8` and always run it on .py files before requesting code review or submiting code.  

## Running unit tests
* Units tests can be run from pycharm by running test_jeeqs.py. You can use a configuration like [this](http://i.imgur.com/pjqvS.png), the two parameters being paths to GAE SDK and Jeeqs' src directory, respectively.

## Code review 
* Create a pull request if you'd like to make a change.
* *Include the output of pep8 whenever requesting code review.*
* *Include the output of running unit tests whenever requesting code review for a change*
* Update your pull request until your have satisfied reviewers. Once you have a confirmation for the change, merge the pull request to master 

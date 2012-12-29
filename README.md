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

* downloading: appcfg.py download_data --url=http://jeeqsy.appspot.com/_ah/remote_api --filename=[db_backup_2012_May_19th] --application=s~jeeqsy
* uploading: appcfg.py upload_data --url=http://localhost:8080/_ah/remote_api --filename=[db_backup_2012_May_19th] --num_threads=1

## Code style
* The standard code style for python files in Jeeqs is [pep8](http://www.python.org/dev/peps/pep-0008/). 
* Install `pep8` and `autopep8` packages and always run them on .py files before requesting code review or submiting code. 

## Code review 
* Create a pull request if you'd like to make a change.
* *Include the output of pep8 whenever requesting code review.*
* *Include the output of running unit tests whenever requesting code review for a change*

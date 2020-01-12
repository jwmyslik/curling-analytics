# Introduction
In this project, I extract data on curling games from shot-by-shot summary
documents that have been made public.  Currently I have done a preliminary
exploration of this data, and taking a look at the stereotype that men prefer
to play a game with more "hit-type" shots than women do.  This only scratches
the surface of what can be done with this dataset, so stay tuned for future
analyses.

A complete write-up of this project is located at:
https://jordanmyslik.com/portfolio/curling-analytics


# Repository Contents
This repository contains the following scripts for creating, populating, and
interacting with the curling_data.db SQLite database:

* setup.sh:  A Bash script for setting up the environment variable that gives the
           path to the database file.

* find_and_download_input_files.py: A Python script that traverses the web page
                                  where the shot-by-shot summaries are stored,
                                  and downloads them to the same directory 
                                  structure on the hard drive.

* convert_data.py:  A Python script that traverses the shot-by-shot summary
                  directory on the hard drive and converts the PDF files into
                  XML files and accompanying PNG images.

* create_database.py:  A Python script that executes the SQL commands required to
                     build the empty tables of the SQLite curling database.

* database_functions.py: A Python library containing a few useful functions for
                       interacting with the database. 

* pdf_parsing_functions.py: A Python library containing all the functions used to
                          extract the data from the XML files and from the PNG 
                          post-shot images of the playing area.

* populate_db.py:  A Python script that goes through the directory of data on the 
                 hard drive, extracts the data from the XML files and PNG images
                 and writes it to the database.

For the proper usage for each of these scripts, see the DocStrings at the
beginning of each script.

This repository also contains Jupyter notebooks with analyses conducted on the
data:

* Curling_Analytics-Preliminary_Data_Exploration.ipynb:  A preliminary
                             exploration of the data in the database.

* Curling_Analytics-Men_vs_Women_Strategy.ipynb: The analysis exploring the
                    stereotype then Men prefer to play the game with more 
                    "hit"-type shots than Women do.


# Setup Notes
The Python scripts above were written and executed using Python 3.7.1 (default,
Dec 14 2018, 19:28:38) [GCC 7.3.0] :: Anaconda, Inc. on linux, running on
Ubuntu 16.04.6 LTS.  Additional libraries used of note:

* cv2: Version 4.1.0
* pandas: Version 0.23.4
* numpy: Version 1.15.4

The Jupyter notebooks were run using Python 3.6.7 |Anaconda custom (64-bit)|
(default, Oct 23 2018, 19:16:44)  [GCC 7.3.0] on linux.  This environment has
the same version of pandas and numpy.  The matplotlib version is 3.0.2.


In all cases, when using the database_functions library, the CADBPATH
environment variable needs to be set to the full path to where the database is
stored.

#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
This script goes through the data directory (or data/<event_name> if an event
name is given on the command line) and executes "pdftohtml -xml" on each of the
shot by shot summary PDF files, to produce more easily readable XML files and
.png images corresponding to the stone placement.

Usage: python convert_data.py (event_name)
event_name: An optional short name, if only want to convert one event's worth of
data.
"""
import glob
import os
import sys

#Get the working directory for this project.
#Since we're switching between paths, need to be relative to this.
working_dir = os.getcwd()

#Now, we want to get the paths to the folders that the shot by shot summaries
#are stored in.
glob_string = "data/"

if len(sys.argv) > 1:
    glob_string += sys.argv[1] + "/*/*/"
else:
    glob_string += "/*/*/*/"

dir_list = glob.glob(glob_string)

#Now that we have a list of the directories with shot by shot summaries, change
#to each of them in turn, get a list of all the .pdf files in them, and execute
#pdftohtml -xml on them.

for file_dir in dir_list:

    os.chdir(file_dir)

    file_list = glob.glob("*")

    for summary in file_list:
        command = "pdftohtml -xml " + summary
        print(command)
        os.system(command)

    #Once we're done with this directory, go back to the original working
    #directory.
    os.chdir(working_dir)

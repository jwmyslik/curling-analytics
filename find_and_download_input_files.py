#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script uses urllib and regular expressions to go through the contents of
http://odf2.worldcurling.co/data/ and download the shot-by-shot summaries into
an identical directory tree in /data in the current working directory.

Has the option of providing a single event short name on the command line to
download just one event's worth of files.  (Useful both for downloading a newly
added event, or for testing.

Usage: python find_and_download_input_files.py (event_short_name)
 event_short_name: Optional specification of one event to download.

If no specific short name is supplied, it downloads all it can find by default.

NB: A quick change was made to deal with some DNS issues crashing this script.
The fix that was used can be found by searching for check_log_file in this
script.  A more robust solution would be more advisable in the future.

"""
import sys
import urllib.request
import re
import time
import os

#Start by checking whether we've been provided a single event_short_name to
#process.  If so, put that in the directory list.  If not, get all of them.
event_directory_list = []
if len(sys.argv) > 1:
    event_directory_list.append("/data/"+ sys.argv[1] + "/")

else:

    response = urllib.request.urlopen("http://odf2.worldcurling.co/data")
    events_html = response.read()
    
    #This regular expression looks for strings wrapped in double-quotes that
    #begin with /data/ and continues for the smallest number of characters
    #possible before reaching a forward slash followed by double-quotation
    #marks.  This is the format of the links on that page.  Note:  Not all of
    #them will contain the files we are looking for, so we must incorporate
    #checks along each step of the way.
    #Only allow 20 characters for the short name.
    #More than sufficient looking at the list, and prevents erroneous matches
    #of this regular expression.
    event_directory_list = re.findall('"/data/.{0,20}?/"', events_html.decode('utf-8'))

#We don't want the quotation marks around the path for future use though, so
#loop through and strip.
for i in range(len(event_directory_list)):
    event_directory_list[i] = event_directory_list[i].strip("\"")

#Now that we have the list of all directories, we can get to work on
#establishing whether they have shot-by-shot summaries, and what directory
#structure we need to reproduce to store them, and pull down the summaries.

#We experienced an issue during downloading, where a failed DNS request crashed
#the program.  To pick up where we left off, at the "event" level check for
#that event directory in the log file (indicates that it was already searched)
#and if it has already been done, skip to the next event immediately.
#Note: You may need to manually delete partial entries for the event in the
#database.
check_log_file = False

#Comment out these lines if you want to do the log file check, and supply the
#name of the log file here.
#check_log_file = True
#log_file = open("data_download.log", "r").read()

#Only considering the traditional men and women games.  These are the
#directories they are stored under.
game_types = ["Men\'s_Teams", "Women\'s_Teams"]
for event_dir in event_directory_list:

    #Before the delay, check whether this event is in the previous log-file.
    if check_log_file and (event_dir in log_file):
        print("Skipping previously handled event directory: " + event_dir, flush = True)
        continue

    #Before we continue, put in a 10 second delay so as not to hammer the web page
    #with requests.
    time.sleep(10)

    #Start by requesting this event directory.
    req_string = "http://odf2.worldcurling.co" + event_dir
    print("Searching " + req_string, flush = True)
    response = urllib.request.urlopen(req_string)
    types_html = response.read()

    #Now, loop over the game types.
    for gt in game_types:

        #Only request the next level of this directory tree if that game type
        #directory exists.
        if re.search(gt, types_html.decode('utf-8')):

            #First, add in the 10 second delay for the server.
            time.sleep(10)

            #Now, pull this game type's directory.

            req_string = "http://odf2.worldcurling.co" + event_dir + gt + "/"
            print("Searching " + req_string, flush = True)           
            response = urllib.request.urlopen(req_string)

            sessions_html = response.read()

            #Now, the subdirectories on this page are the ones that contain the
            #shot by shot summaries.  So get an array of subdirectories to
            #traverse.
            session_dirs = re.findall('"' + event_dir + gt + '/.*?/"',sessions_html.decode('utf-8'))

            #session_dirs should now contain the full path to all the different
            #session directories.  Loop through them, request each page, get
            #the list of shot by shot summaries, and download them to the same
            #directory structure starting in the current working directory.
            for path in session_dirs:

                #Delay 10 seconds for the server.
                time.sleep(10)

                #Remember to strip out the extra quotations in the path.
                path = path.strip("\"")
                
                req_string = "http://odf2.worldcurling.co" + path
                print("Searching " + req_string, flush = True)
                response = urllib.request.urlopen(req_string)
                pdfs_html = response.read()

                summary_paths = re.findall('"' + path + '.{0,20}?_Shot_by_Shot_.*?.pdf"',pdfs_html.decode('utf-8'))
                
                #Now, if summary_paths is not empty, verify (or create) the
                #directory structure we need to save those files.
                #Get the full directory structure by splitting this
                #string on the forward slash.
                #Strip off any leading and trailing forward slashes, so
                #this list only contains various names, and no empty
                #strings.
                #dir_path stores the path as we go deeper into the directory
                #structure.
                if(len(summary_paths) == 0):
                    print("No summary files found.  Switching to new directory.", flush = True)
                    continue
                else:
                    print(str(len(summary_paths)) + " summary files found. Saving...", flush = True)


                dir_list = path.strip("/").split("/")
                dir_path = ""
                for dir_name in dir_list:
                    if not os.path.exists(dir_path + dir_name):
                        os.mkdir(dir_path + dir_name)

                    dir_path += dir_name + "/"

                
                #Now, loop through the summary paths and save each file to its
                #place in the directory structure.
                for summary in summary_paths:

                    #First, remove any extra quotation marks.
                    summary = summary.strip("\"")

                    #Now, open the url and read the file, after a 10 second
                    #delay.
                    time.sleep(10)
                    response = urllib.request.urlopen("http://odf2.worldcurling.co" + summary)
                    pdf_file = response.read()

                    #Now, create the output file.
                    #The "w" option is for "write"
                    #The "b" option is for "bytes", which is what the PDF comes
                    #as in the response.
                    #And initial and trailing slashs from summary to get the
                    #right path.
                    out_file = open(summary.strip("/"), "wb")
                    out_file.write(pdf_file)
                    out_file.close()



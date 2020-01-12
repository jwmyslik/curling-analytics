#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
This script goes through all the xml and .png files in data (or data/<event_name> if an event
name is given on the command line) 
On completion of running this script, the database should be populated with all
the contents of the data directory.

To facilitate adding new events (and for testing) a single-event mode is
available by specifying a short name on the command line.

Usage: python populate_db.py (short_name)
    short_name is the optionally specified short name of an event, for single
event mode.

"""
import database_functions as db
from datetime import datetime
import pdf_parsing_functions as pf
import glob
import sys
import os
import xml.etree.ElementTree as ET


#Get the current working directory, so we can go back up to it later.
working_directory = os.getcwd()

#Where we want to look for the data (nominally the data/ directory).
starting_directory = "data/"

#Change directory to the starting directory.
os.chdir(starting_directory)

#If one event short name was supplied on the command line, put that in our
#short names list.  Otherwise, pull up the list of short names with glob.
#NB: We will sort all glob.glob output, because this should give us an order
#that makes some sense, which helps during testing.
short_names = []

if len(sys.argv) > 1:
    short_names.append(sys.argv[1])

else:
    short_names = glob.glob("*")
    short_names = sorted(short_names)

#We'll build the database by going through the directory tree.  


#Loop over the short names of each of the events to loop over the events.
for event in short_names:

    #These are the variables we must set for each event that go into the
    #database.
    #id: ID number of this event, the primary key.
    #name_short: The abbreviation for this event's name.
    #start_date: The start date of this event.
    #end_date: The end date of this event.
    #NB: The last 2 require input from the shot by shot summary files to
    #   fill.
    #start_date and end_date should be taken by finding the extrema of the
    #game start dates for this event.
    #So write out the event to the database as soon as pull the information from the
    #PDF file, and update it with start and end date before moving on to the
    #next event.
    event_id = db.get_next_id("events")
    event_name = event
    event_start_date = ""
    event_start_datetime = datetime.max  #Since use less than comparison of game
                                   #dates to set this value.
    event_end_date = ""
    event_end_datetime = datetime.min  #Since use greater than comparison of game
                                   #dates to set this value.

    #Since we now have enough information to create this event entry, do so.
    c = """
        INSERT INTO events (
            id, 
            name)
            VALUES (
            "{}",
            "{}");
            """
    db.run_command(c.format(event_id, event_name))


    #Next directory level is type.  Change directory to this event's directory,
    #then use glob to grab.
    os.chdir(event)
    game_types = glob.glob("*")
    game_types = sorted(game_types)
    for gt in game_types:

        #Change to the game type directory in question.
        os.chdir(gt)

        #The game_type for saving to the database (in the games table) is
        #either "Men" or "Women" (at least at this point), so convert gt to
        #that.
        game_type = ""
        if gt == "Men\'s_Teams":
            game_type = "Men"
        elif gt == "Women\'s_Teams":
            game_type = "Women"
        else:
            game_type = "Unknown"


        #The rest of the information we need can be taken directly from the
        #shot-by-shot summary files.  So descend down to that directory level
        #and loop through those.
        session_names = glob.glob("*")
        session_names = sorted(session_names)
        for session in session_names:
            
            #Change to the session directory, and pull up the list of xml files we
            #will pull information from.
            os.chdir(session)
            xml_files = glob.glob("*.xml")
            xml_files = sorted(xml_files)

            #Add in a print statement so we know that something is
            #happening.
            print("Processing: " + event + " " + session)

            #Loop over the xml files, and pull out the information we need.
            for gf in xml_files:

                #This is the list of variables we need to write to the
                #database in the "games" table:
                game_id = db.get_next_id("games")
                
                #We also write the current event_id values.
                #We already extracted the game_type above.
                
                #The session is everything after the last "~" in the directory
                #name
                game_session = session[session.rindex("~") + 1:]
                
                #The rest of these come from the PDF file.
                game_red = ""
                game_yellow = ""
                game_red_score = 0
                game_yellow_score = 0
                name_and_sheet = {}
                date_and_time = {}
                first_shot_color = ""
                team_to_color = {}
                color_to_team = {}


                #Loop through the xml file.  Each individual page corresponds
                #to an end.
                tree = ET.parse(gf)
                pages = tree.getroot()
                for ip in range(len(pages)):

                    #If it's the first page, extract the game wide information
                    #that can from there.
                    #Get the image list on every page, as we need that for the
                    #shot-by-shot information, and the end information that
                    #needs to be extracted from the shot information.
                    image_list = pf.get_image_list(pages[ip])
                    if ip == 0:
                        name_and_sheet = pf.get_name_and_sheet(pages[ip])
                        date_and_time = pf.get_date_and_time(pages[ip])

                        #At this point we have all the information we need to
                        #create a basic entry for this game in the database.
                        #As with the event table, the data is not complete at
                        #this point, but we have to create an entry so we can
                        #create the ends, shots, and stone_positions tables.
                        c = """
                        INSERT INTO games (
                        id,
                        event_id,
                        session,
                        name,
                        sheet,
                        type,
                        start_date,
                        start_time)
                        VALUES (
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}");
                        """
                        db.run_command(c.format(game_id, event_id, session,
                            name_and_sheet["name"], name_and_sheet["sheet"],
                            game_type, date_and_time["date"],
                            date_and_time["time"]))

                        #Also compare the date of this event to the stored
                        #event start and end dates, so can establish the date
                        #bounds of the event for writing to the event table. 
                        curr_datetime = datetime.strptime(date_and_time["date"], "%a %d %b %Y")

                        if(curr_datetime < event_start_datetime):
                            event_start_datetime = curr_datetime
                            event_start_date = date_and_time["date"]

                        if(curr_datetime > event_end_datetime):
                            event_end_datetime = curr_datetime
                            event_end_date = date_and_time["date"]

                    #Each page corresponds to an end.  So get out the
                    #information we need to start the end entry.
                    end_id = db.get_next_id("ends")
                    
                    #The end number is just the page number (page index plus
                    #one)
                    end_number = ip + 1

                    #The rest of the information we need to look at the shots
                    #at, so create the ends table entries now an update them
                    #later with shot information.
                    c = """
                    INSERT INTO ends(
                    id,
                    game_id,
                    number)
                    VALUES(
                    "{}",
                    "{}",
                    "{}");
                    """
                    db.run_command(c.format(end_id, game_id, end_number))

                    #Now, loop through the list of images to extract shot by
                    #shot data.
                    #Store the previous maximum element index in the loop
                    #through the elements in the page for each shot, so that we
                    #don't have to waste time looping over elements we've
                    #already considered.
                    prev_max_elt_index = 0
                    
                    #Use the first shot color to get the color with the hammer
                    #(the other color), and the direction of play.
                    color_hammer = ""
                    direction_of_play = ""
                    for si in range(len(image_list)):
                        
                        #First, get a new shot_id for this shot.
                        shot_id = db.get_next_id("shots")

                        #Convert the shot index to shot number.
                        shot_number = si + 1


                        #Next, get the rock positions as a dataframe by
                        #passing the image path to the get_rock_positions
                        #function.
                        #This function takes the path to the image, which is in
                        #the "src" attribute of this element.
                        stone_df = pf.get_rock_positions(image_list[si].attrib["src"])

                        #Now, if it's the first shot, extract the direction of
                        #play, get the first shot color too. 
                        if si == 0:
                            direction_of_play = pf.get_direction_of_play(stone_df)
                            first_shot_color = pf.get_1st_shot_color(stone_df)

                            #The team with the hammer is the team color that
                            #does not.
                            if first_shot_color == "red":
                                color_hammer = "yellow"
                            elif first_shot_color == "yellow":
                                color_hammer = "red"
                            else:
                                color_hammer = "error_color"

                            bool_dir_of_play = 0
                            if direction_of_play == "up":
                                bool_dir_of_play = 1

                            #Update the end table with the hammer color and the
                            #direction of play.
                            c = """
                            UPDATE ends
                            SET direction = "{}", color_hammer = "{}"
                            WHERE id = "{}";
                            """
                            db.run_command(c.format(bool_dir_of_play, color_hammer, end_id))
                            
                        

                        
                        #Now that we have the direction of play and the color
                        #of the first shot, standardize to one coordinate
                        #system and clean out all but the stones in play.
                        stone_positions = pf.clean_rock_positions(stone_df,
                            direction_of_play)

                        #Now, get the data for this shot.
                        shot_data = pf.get_shot_data(pages[ip], si + 1,
                            image_list, prev_max_elt_index)

                        #If this is the first shot of the first end, use this
                        #information to map team to shot color.
                        if (si == 0) and (ip == 0):
                            team_to_color[shot_data["team"]] = first_shot_color
                            

                        #If it's the second shot of the first end, fill in the
                        #other team's name and shot color (i.e. color_hammer)
                        elif (si == 1) and (ip == 0):
                            team_to_color[shot_data["team"]] = color_hammer

                            #Now fill the color_to_team variable, for easy
                            #conversion the other way.
                            for elt in team_to_color.items():
                                color_to_team[elt[1]] = elt[0]


                            #At this point we have the information we need to
                            #update this game's database entry with the team
                            #names.
                            c = """
                            UPDATE games
                            SET team_red = "{}", team_yellow = "{}"
                            WHERE id = "{}";
                            """
                            db.run_command(c.format(color_to_team["red"],
                                color_to_team["yellow"], game_id))



                        #Extract the maximum element index for use in the next
                        #shot.
                        prev_max_elt_index = shot_data["max_elt_index"]

                        #At this point we should have all the shot data we need
                        #to assemble a full record. Do so now.
                        c = """
                        INSERT INTO shots (
                        id,
                        end_id,
                        number,
                        color,
                        team,
                        player_name,
                        type,
                        turn,
                        percent_score)
                        VALUES (
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}");
                        """
                        db.run_command(c.format(shot_id,
                            end_id, 
                            shot_number,
                            team_to_color[shot_data["team"]],
                            shot_data["team"],
                            shot_data["player_name"],
                            shot_data["type"],
                            shot_data["turn"],
                            shot_data["percent_score"]))

                        #Now that there is an entry for the shot data, we can
                        #write out the stone positions for this shot.
                        #stone_positions already contains all the data for this
                        #shot, so we just need to iterate over it and write
                        #each row to the database.
                        for sp_index, sp_row in stone_positions.iterrows():
                            stone_id = db.get_next_id("stone_positions")

                            c = """
                            INSERT INTO stone_positions(
                            id,
                            shot_id,
                            color,
                            x,
                            y)
                            VALUES (
                            "{}",
                            "{}",
                            "{}",
                            "{}",
                            "{}");
                            """
                            db.run_command(c.format(stone_id,
                                shot_id,
                                sp_row["color"],
                                sp_row["x"],
                                sp_row["y"]))
                        

                    #On every page we need to extract the score and the time
                    #left.
                    score_and_time = pf.get_score_and_time(pages[ip], 
                        prev_max_elt_index)


                    #Only deal with the score and time remaining if the box is
                    #present (the score_and_time variable is not None.
                    if(score_and_time is not None):
                   
                        #Fill score and time remaining for the end.
                        c = """
                        UPDATE ends
                        SET score_red = "{}", score_yellow = "{}",
                        time_left_red = "{}", time_left_yellow = "{}"
                        WHERE id = "{}"
                        """
                        db.run_command(c.format(score_and_time["score"][color_to_team["red"]],
                            score_and_time["score"][color_to_team["yellow"]],
                            score_and_time["time_left"][color_to_team["red"]],
                            score_and_time["time_left"][color_to_team["yellow"]],
                            end_id))


                        #If it's the last page, fill the final score variable
                        #and write it to the database.
                        if ip == len(pages) - 1:
                            game_red_score = score_and_time["score"][color_to_team["red"]]
                            game_yellow_score = score_and_time["score"][color_to_team["yellow"]]
                            c = """
                            UPDATE games
                            SET final_score_red = "{}", final_score_yellow = "{}"
                            WHERE id = "{}";
                            """
                            db.run_command(c.format(game_red_score,
                                game_yellow_score, game_id))



               


            #Now that we're done with the session, go up one level so we can
            #continue to the next session.
            os.chdir("..")

        #Now that we've gone through all the session, go up one level to the
        #game types directory.
        os.chdir("..")


    #Now that we've gone through all the game types, go up one level so we can
    #pull the next event.
    os.chdir("..")

    #Update the event entry with the start and end dates before proceeding to
    #the next event.
    c = """
    UPDATE events
    SET start_date = "{}", end_date = "{}"
    WHERE id = "{}";
    """
    db.run_command(c.format(event_start_date, event_end_date, event_id))


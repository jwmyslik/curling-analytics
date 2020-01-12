#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
The various functions we need to parse the PDF files and extract the data they
contain are defined and implemented here.
"""

import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
import cv2

def get_rock_positions(image_path):
    """
    Given a path to the standard sheet overview (image_path) as a string, returns a
    pandas DataFrame with all rock positions in terms of pixel positions in
    the image, and the rock color (Red or Yellow), and the size of the rock
    (useful for removing the unthrown ones without a position cut that could
    prove problematic in the extreme edge case of a rock that isn't fully past the hog
    line but is still in play because it collided  with a rock past the hog line.
    
    NB: The output requires further post-processing to flip the rocks to the correct
    coordinate system (origin at the center of the button) and extract the
    direction of play, as well as remove the rocks that are out of play or yet
    to be thrown.
    """
    
    #The discussion here indicates that assembling a list of dicts for each row
    #is a pretty fast way of getting a structure we can easily convert to a
    #DataFrame.  So set that up now:
    #https://stackoverflow.com/questions/10715965/add-one-row-to-pandas-dataframe
    row_list = []

    #Dictionary keys will be ["color", "x", "y", "size"] 


    #Start by reading in the image.
    img = cv2.imread(image_path)

    #Convert this to a binary image for each stone color.
    #(White where the stones are, black everywhere else).
    #Red stones are just solid red circles
    red_bin = cv2.inRange(img, (0, 0, 255), (0, 0, 255))

    #Yellow stones that have been thrown already are yellow circles that also
    #have an X in them that is part blue and part greyish-yellow.  So that the
    #contour finding works properly, we need to OR all these binary images
    #together so that played rock contours are detected as circles.
    #In most cases yellow is (B,G,R) = (0,255,255).  It looks like when the
    #house is yellow-ish sometimes it is darker.  So expand the range to allow
    #(0,193,255).  Should still be specific enough not to trigger on the house.
    #In this case, blue takes on a little bit of green too.
    #Also need to expand greyish-yellow out to allow (0, 178, 239)
    yellow_bin = cv2.inRange(img, (0,192,255), (0,255,255))
    blue_bin = cv2.inRange(img, (255,0,0),(255,63,0))
    
    #Greyish-yellow appears to employ two shades in some instances.  Use them
    #as the bounds of the range.
    #Original before the "off yellow" expansion:
    #(32,207,207), (32,223,223)
    #Increse G by 1 for another shade of grey found (sometimes (rarely) a black X is
    #used through the yellow stones.  Adding black is problematic for this
    #algorithm though (triggers on all the lines), so will not do that.
    greyish_yellow_bin = cv2.inRange(img, (0,164,207), (32,224,239))
    
    yellow_rocks = cv2.bitwise_or(yellow_bin, cv2.bitwise_or(blue_bin,
        greyish_yellow_bin))

    #Loop over red and yellow, and fill the row_list, one rock position per
    #row.
    rock_bin_dict = {"red":red_bin, "yellow":yellow_rocks}.items()
    for color, rock_bin in rock_bin_dict:

        #Get the contours, using RETR_TREE so can use hierarchy to remove contours within
        #contours (unfilled circles denoting positions of rocks that were
        #moved)
        contours, hierarchy = cv2.findContours(rock_bin, cv2.RETR_TREE,
                cv2.CHAIN_APPROX_NONE)

        #We want to remove all contours that have contours within them or are
        #within contours, as these are former positions of rocks, which we
        #don't need to store.
        #Such contours have parents or children (the last 2 entries in the
        #hierarchy for the contour), so we need to only keep contours whose
        #last 2 hierarchy numbers are both -1.
        only_rocks = np.array(contours)[np.all(hierarchy[0,:,2:4] == -1,
            axis=1)]

        #Finally, loop over the remaining contours in only_rocks and get the
        #centroids to get the rock positions, appending them with their color
        #to row_list.
        #Note: In the case of partial rock previous positions, the area, M['m00'],
        #comes up as zero.  To guard against division by zero, divide by the
        #maximum of M['m00'] and 1.
        for cnt in only_rocks:
            M = cv2.moments(cnt)
            cx = M['m10']/max(M['m00'], 1)
            cy = M['m01']/max(M['m00'], 1)

            row_list.append({"color":color, "x":cx, "y":cy, "size":M['m00']})



    #Now that we've looped over both colors and all rocks with those colors,
    #turn the row_list to a DataFrame and return it.
    return pd.DataFrame(row_list)


def get_direction_of_play(rock_df):
    """
    Which end of the sheet is being played on in a given end is useful
    information, as the ice conditions depend on it.  We can determine this by
    supplying the rock dataframe for the first shot of the end to this
    function, which then returns "up" if the house is at the top of the image,
    or "down" if the house is at the bottom of the image.  It does this by
    checking whether the unplayed rocks are at the top of the page (corresponds
    to "down", or the bottom of the page "up".  We use this information later
    to convert all rock positions to the "down" coordinate system, for easy
    comparison from the skip's eye view.

    This is done by counting whether there are more stones in the top 20 pixels
    of the sheet, or the bottom 20 pixels of the sheet.
    """
    n_top_20 = (rock_df["y"] < 20).sum()
    n_bottom_20 = (rock_df["y"] > 579).sum()

    #If there are more at the top than the bottom after the first shot, it's
    #"down"
    if n_top_20 > n_bottom_20:
        return "down"

    #Otherwise, it's "up"
    else:
        return "up"



def clean_rock_positions(rock_df, direction):
    """
    Given a dataframe of rock colors and the direction of play (up or down):
    -Convert all positions to the "down" coordinate system, so only have to
    make cuts on one value for out of play and unthrown rocks. 
    -Remove rocks that haven't been thrown yet.
    -Remove rocks that are out of play.
    -Change coordinates so that the button is (0,0),
    left is negative, right is positive, in front of the t-line is positive,
    and behind the t-line is negative.  This is how one would view the sheet
    as the skip, standing behind the house and calling the shots.
    
    Note:  Was going to convert the pixel coordinates to distance in inches
    based on the button, 4 ft, 8 ft, and 12 ft diameter rings, but it turns out
    that the scaling is non-linear (if you calculate inches/pixel for each you
    get different answers).  The most egregious offender is the button, whose
    radius is double what it should be, given the size of the rest of the
    rings.  Makes sense to want to show detail better closer in.  Best solution
    is to leave everything in pixel coordinates for the dataset.  If one is
    interested in coordinates based on real measurements, that can be done in
    post-processing using the various house coordinates.

    This function returns the modified DataFrame.

    The images are all 300x600, so 0-299 in x, and 0-599 in y. 
    """
    
    #First, if the direction is "up", flip horizontally and vertically to
    #change to the "down" coordinate system.
    #HOWEVER, it turns out that a flipped "up" requires some translation to be
    #perfectly aligned with a "down" configuration.  (Which is  to be expected,
    #because there are an even number of pixels in each dimension, so there is
    #no invariant axis in the image.  i.e. the centre-line is off-centre) We'll take this into
    #account by using the centre of the button (the "pin") as the reference point, as this
    #becomes the origin.
    #This is the value for "down"
    pin = (149, 439)
    if direction == "up":
        rock_df["x"] = 299 - rock_df["x"]
        rock_df["y"] = 599 - rock_df["y"]
        
        #This is where the pin is in a flipped "up".
        pin = (150, 440)

    #Now, to remove all the rocks that haven't been played yet, filter out all
    #rocks with a size lower than 100 (the unthrown rocks seem to have size 30,
    #and the thrown rocks between 150 and 230, so this seems like  a good
    #place to put the cut and have lots of wiggle room.
    #NB: This cut also removes partial contours of previous rock positions that
    #intersect with current rock positions (leading to an incomplete hollow
    #circle, that contour detection sees as a small enclosed region.
    rock_df = rock_df[rock_df["size"] > 100]

    #All the rocks that have gone out of play get lined up along the bottom
    #line.  Also need to be careful here, since rocks still in contact with the
    #back line are still in play.  This "thrown rock storage area" is 40 pixels
    #deep, and rocks are approximately 8 pixels in radius, so cutting any rock
    #with a centroid with y >= 580 should provide sufficient wiggle room on both
    #sides.
    rock_df = rock_df[rock_df["y"] < 580]
    
    
    #Since we're remaining in pixel coordinates, change to the pin-centric
    #coordinate system now.
    #For x runs from 0 to 299 left to right, so just need to subtract the pin
    #x position for the correct x coordinate.
    rock_df["x"] = rock_df["x"] - pin[0]

    #y runs from 0-599 top to bottom, so need to subtract the y position from
    #the y pin position to flip the orientation.
    rock_df["y"] = pin[1] - rock_df["y"]


    #We don't need the rock size in our dataset, so remove that column.
    rock_df = rock_df.drop(columns=["size"])
    
    #Also, reset the index so that it is sequential from zero for the rocks
    #that we do have in play.
    rock_df = rock_df.reset_index(drop=True)
    
    return rock_df


def get_1st_shot_color(df):
    """
    When given the output of get_rock_positions for the 1st shot, returns the
    color of the team that shot that shot.  (i.e. sees who has 7 shots
    remaining.)  Useful for the very first shot of the game, when need to
    figure out the team name abbreviations and which color stone each time is
    shooting.
    """
    #Select only the rocks with size less than 100.
    #Since we only use this on the first shot, there cannot be any previously
    #played rock positions, so this cut can only possibly select the unthrown
    #rocks.
    rock_df = df[df["size"] < 100]
    n_red = rock_df["color"][rock_df["color"] == "red"].count()
    n_yellow = rock_df["color"][rock_df["color"] == "yellow"].count()
    
    if n_red == 7:
        return "red"

    elif n_yellow == 7:
        return "yellow"
    else:
        return "color_error"


def get_date_and_time(page):
    """
    Given a page from the xml file, pulls out the date and time of the game and
    returns them as a dict with keys ["date", "time"].
    """
    
    #Loop over all the elements in the page to find the start time,
    #and save its value along with its left and top positions, and its index
    #number so we can identify it when checking for the start_date.
    start_time = ""
    start_time_left = 0
    start_time_top = 0
    start_time_index = 0
   

    for i in range(len(page)):
        
        elt = page[i]
        
        #If this isn't a text element, continue to the next one.
        if elt.tag != "text":
            continue

        #If the length of the elt is equal to 1, it means that there is a <b>
        #</b> tag that indicates bold in the original PDF.  In that case, do
        #elt[0] instead of elt.
        #NB:  Still need to retain elt for the attribute information.
        text_elt = elt
        if(len(elt) == 1):
            text_elt = elt[0]


        #The element with the start time contains "Start Time".  If we find
        #this element, save the information we need then break out of the loop.
        if "Start Time" in text_elt.text:

            #If we split this text by space, the actual time is the last
            #element.
            start_time = (text_elt.text).split(" ")[-1]
            start_time_left = int(elt.attrib["left"])
            start_time_top = int(elt.attrib["top"])
            start_time_index = i

            break

    #Now, loop through the elements again.  Find the first element with the
    #same left value, and a top value that is less than 30 below that of the
    #start time (the date has the same left justification, but is slightly
    #above the time.)
    game_date = ""
    for i in range(len(page)):
        
        #If this is the start time element, continue.
        if i == start_time_index:
            continue
        
        elt = page[i]
       
        #If this isn't a text element, continue to the next one.
        if elt.tag != "text":
            continue

        #If the length of the elt is equal to 1, it means that there is a <b>
        #</b> tag that indicates bold in the original PDF.  In that case, do
        #elt[0] instead of elt.
        #NB:  Still need to retain elt for the attribute information.
        text_elt = elt
        if(len(elt) == 1):
            text_elt = elt[0]


        elt_left = int(elt.attrib["left"])
        elt_top = int(elt.attrib["top"])

        #If the positioning indicates it's the date element, fill in the date
        #info.
        if (elt_left == start_time_left) and (abs(start_time_top - elt_top) < 30):
            game_date = text_elt.text
            break

    return {"date":game_date, "time":start_time}



def get_image_list(page):
    """
    Goes through a page and returns (in order) all elements for images in the page if the
    images are 116x232 (i.e. the image size of the shot position images). This
    list is used both to get the proper positions for the shot data, and to
    pass images to the house diagram extraction functions.
    """
    image_width = 116
    image_height = 232

    image_list = []
    for i in range(len(page)):

        if ((page[i].tag == "image") 
                and (int(page[i].attrib["width"]) == 116)
                and (int(page[i].attrib["height"]) == 232)):

            image_list.append(page[i])

    return image_list




def get_shot_data(page, shot, image_list, prev_max_elt_index = 0):
    """
    Given a page from the xml file, the shot number under consideration, and
    the image attributes array for all the stone position images after each
    shot, returns a dictionary of the shot data with keys ["team",
    "player_name", "type", "turn", "percent_score", "max_elt_index"]

    max_elt_index is the index of the page element this information was
    extracted from with the largest value.  This function optionally takes that
    index value for the previous shot as a way to speed up looping through the page (so we don't need
    to check the position of shots we've already extracted the data from
    against the expected position of the current shot's information.)
    
    For each shot, all the information we're looking for (team + player_name),
    type, turn, and percent score is bounded by the following:
        -Image Left - 5
        -Image Left + Image Width
        -Image Top + Image Height
        -Image Top + Image Height + 30 

    So, starting at prev_max_elt_index, we loop through the elements until we
    find one that satisfies those 4 conditions.  We keep saving those elements
    until we find one that does not satisfy those conditions.

    Then, we order by top to bottom, left to right, and then they are ordered
    as:
    1. team: player name
    2. type
    3. turn
    4. percent_score: NB: If 1-4, multiply by 25 to convert from 4 point system
    to percent.
    
    Take the greatest index number for max_elt_index.

    If there are fewer than 4 entries, that means it's a "no statistics" shot,
    so only write out team and player name, which is all the information
    typically included here. (The other two entries in this case are "no
    statistics" and "-".
    
    """
    
    #image_list is a list of the stone elements in ascending order, as
    #selected elsewhere by the image size (all stone images are 116 wide by 232
    #in height.
    elt_shot_image = image_list[shot - 1]
    left_bound = int(elt_shot_image.attrib["left"]) - 5
    right_bound = int(elt_shot_image.attrib["left"]) + int(elt_shot_image.attrib["width"])
    top_bound = int(elt_shot_image.attrib["top"]) + int(elt_shot_image.attrib["height"])
    bottom_bound = top_bound + 30

    #Store the elements that satisfy the boundary conditions in a dictionary by
    #index number, for easy extraction of the maximum index.
    elt_dict = {}

    #Loop over the elements in the page, starting at prev_max_elt_index.
    #Keep track of whether we've found the first acceptable instance, because
    #this allows us to stop the loop once we've gone out of range, saving some
    #processing time.
    first_instance_found = False
    for i in range(prev_max_elt_index, len(page)):

        #If this isn't a text element, continue to the next one.
        #(other element types are not guaranteed to have these positioning
        #attributes)
        if page[i].tag != "text":
            continue

        gl = int(page[i].attrib["left"]) > left_bound
        lr = int(page[i].attrib["left"]) < right_bound
        gt = int(page[i].attrib["top"]) > top_bound
        lb = int(page[i].attrib["top"]) < bottom_bound

        in_range = gl and lr and gt and lb

        if in_range:
            elt_dict[i] = page[i]
            first_instance_found = True


        if first_instance_found and not in_range:
            break

    #Alright, so at this point we want to know the maximum index.
    max_elt_index = max(elt_dict.keys())

    elt_list = elt_dict.values()
    
    #Now, to get the remaining information, it looks like sometimes the turn
    #has a position slightly higher than the other items on the bottom row, so
    #sorting top to bottom and left to right doesn't work.
    #HOWEVER, the top element with the team and player name always has a colon
    #in it, a property shared by none of the fields.  So just sort left to
    #right, and extract the team and player name when we see the colon. 
    sorted_elts = sorted(elt_list, key = lambda x: int(x.attrib["left"]))

    #Create our output dictionary and fill it.
    output_dict = {"team":None, "player_name":None, "type":None, "turn":None,
            "percent_score":None, "max_elt_index":max_elt_index}
    
    #If this is a no-statistics shot, we don't want to try and save things that
    #don't exist.  Just leave them as None in the output dictionary.
    no_statistics_shot = len(sorted_elts) < 4
    bottom_row_index = 0
    bottom_row_labels = ["type", "turn", "percent_score"]
    

    #It looks like sometimes they put extra information below this shot
    #data (e.g. "picked up debris").
    #So , look at the sorted elements.  If there are too many (indicating
    #some extra information added there), remove the one with the largest top
    #value.
    if len(sorted_elts) > 4:
        sorted_top = sorted(elt_list, key = lambda x: int(x.attrib["top"]))
        sorted_elts = sorted(sorted_top[:-1], key = lambda x: int(x.attrib["left"]))



    for i in range(0, len(sorted_elts)):
       
        elt = sorted_elts[i]
        elt_text = elt.text
        
        #Do a check for bold here just in case.)
        if len(elt) == 1:
            elt_text = elt[0].text

        #First, check for the colon, and if it's there, fill in the team and
        #player name values.
        if ":" in elt_text:
            info_list = elt_text.split(":")
            output_dict["team"] = info_list[0]
            output_dict["player_name"] = info_list[1].strip(" ")

        elif not no_statistics_shot:
            
            output_dict[bottom_row_labels[bottom_row_index]] = elt_text
            bottom_row_index += 1

    
    #Now, need to do some massaging of the outputs.  First, "turn" is often
    #given by a special character.  Want to convert to "clockwise" or
    #"counterclockwise"
    if output_dict["turn"] == "↻":
        output_dict["turn"] = "clockwise"

    if output_dict["turn"] == "↺":
        output_dict["turn"] = "counterclockwise"

    #Also, unify the scores to a percentage numerical value.
    #First, strip any percent signs and convert to integers. 
    if output_dict["percent_score"] is not None:
        
        output_dict["percent_score"] = output_dict["percent_score"].strip("\%")

        #If the value is not convertable to an integer, assign is as None.
        if not output_dict["percent_score"].isdigit():
            output_dict["percent_score"] = None

        #Otherwise convert it to an integer.
        else:
            output_dict["percent_score"] = int(output_dict["percent_score"])


        #Also, if a 4 scale was used, multiply by 25 to give a percent value.
        four_scale = [1,2,3,4]
        if output_dict["percent_score"] in four_scale:
            output_dict["percent_score"] = output_dict["percent_score"]*25


    return output_dict


def time_left_to_seconds(time_string):
    """
    A simple function to convert the time remaining from MM:SS to seconds.
    """
    minutes = int(time_string.split(":")[0])
    seconds = int(time_string.split(":")[1])

    return minutes*60 + seconds

def get_score_and_time(page, start_index = 0):
    """
    Give a page from the xml file, 
    extract the score at the end of this end,
    and the time remaining in seconds.
    Returns a dict with key names equal to the team names.  User needs to
    convert to team colors.
    These are done together as they are located in the same box at the bottom
    right hand corner of each page.

    Includes an optional start index (can feed it the max index for data in the
    last shot) to not loop through already checked entries unnecessarily.

    Output format is {score: {TEAM1:VAL1 , TEAM2:VAL2 }, time_left:{TEAM1:VAL1,
    TEAM2: VAL2}}, or just None if the box with this information is not
    included.

    NB:  Some files seem to neglect to include this box.  This information does
    exist in other areas in those files, but is more difficult to extract.
    We'll wait to see how often that happens before determining whether it's
    worth trying to extract.  So we initially need to do a check for "Total
    Score", and if that is not gound, just return None values.

    This method works as follows:
    1. Look for "Total Score" to get the top position of the "Total Score" row.
    2. Look for "Time left" to get the top position of the "Time left" row.
    3.  Grab all the text elements within 30 units above Total Score and 30
    units below Time left, and to their right.  This list will contain:
    i) Two country codes on the top.
    ii) Two Total Score values in the middle.
    iii) Two Time left (in MM:SS format)

    Just sort this list top to bottom and left to right.  The resulting list
    will then be:
    [NAME1, NAME2, Score1, Score2, Time1, Time2].  Put into the correct output
    format accordingly.
    """
    score_top = 0
    score_left = 0
    time_top = 0
    time_left = 0
    for i in range(start_index, len(page)):
        
        #If this isn't a text element, continue to the next one.
        #(other element types are not guaranteed to have these positioning
        #attributes)
        if page[i].tag != "text":
            continue

        elt_text = page[i].text
        
        #Do a check for bold here just in case.)
        if len(page[i]) == 1:
            elt_text = page[i][0].text

        if "Total Score" in elt_text:
            score_top = int(page[i].attrib["top"])
            score_left = int(page[i].attrib["left"])

        elif "Time left" in elt_text:
            time_top = int(page[i].attrib["top"])
            time_left = int(page[i].attrib["left"])


    #If score_left is still zero, it means that it was not found in the
    #document, so return None.
    if score_left == 0:
        return None

    #Otherwise, set up our bounds an extract the elements satisfying them.
    upperbound = score_top - 30
    lowerbound = time_top + 30
    leftbound = score_left + 1

    #Now, loop over elements again to pull out the country names, scores, and
    #time remaining.
    data_elts = []
    for i in range(start_index, len(page)):
        
        #If this isn't a text element, continue to the next one.
        #(other element types are not guaranteed to have these positioning
        #attributes)
        if page[i].tag != "text":
            continue

        elt_text = page[i].text
        
        #Do a check for bold here just in case.)
        if len(page[i]) == 1:
            elt_text = page[i][0].text

        elt_left = int(page[i].attrib["left"])
        elt_top = int(page[i].attrib["top"])

        if (elt_left > leftbound) and (elt_top > upperbound) and (elt_top < lowerbound):
            data_elts.append(page[i])


    #Now that we have all matching elements, sort them top to bottom and left
    #to right.
    sorted_elts = sorted(data_elts, key = lambda x: (int(x.attrib["top"]), int(x.attrib["left"])))
    output_dict = {}

    #In some (only found one) cases, instead of putting the score, the game was just scored as
    #Win/Loss (W and L).  So, we need to check for that and swap them for
    #numbers (999 for W, 0 for L) before inserting into the output_dict.
    scores = [sorted_elts[2].text, sorted_elts[3].text]
    for si in range(len(scores)):

        if scores[si] == "W":
            scores[si] = 999
        elif scores[si] == "L":
            scores[si] = 0

        else:
            scores[si] = int(scores[si])


    output_dict["score"] = {sorted_elts[0].text:scores[0],
            sorted_elts[1].text:scores[1]}
    output_dict["time_left"] = {sorted_elts[0].text:time_left_to_seconds(sorted_elts[4].text),
            sorted_elts[1].text:time_left_to_seconds(sorted_elts[5].text)}

    return output_dict



def get_name_and_sheet(page):
    """
    A function to extract the game and sheet name from the document.  Just need
    to find the element with "Sheet" in the text, and then split on the
    "Sheet", and strip off any additional spaces or dashes.
    There is some variability in the naming here (sometimes it will match the
    Session name, sometimes it will be a subdetail, e.g. "Group B".).  Returns
    a dict {name: GAMENAME, sheet:SHEET}.
    """
    for i in range(len(page)):
        
        #If this isn't a text element, continue to the next one.
        #(other element types are not guaranteed to have these positioning
        #attributes)
        if page[i].tag != "text":
            continue

        elt_text = page[i].text
        
        #Do a check for bold here just in case.)
        if len(page[i]) == 1:
            elt_text = page[i][0].text


        #Now if the string "Sheet" is in the text, extract the information and
        #return.
        if "Sheet" in elt_text:
            
            text_array = elt_text.split("Sheet")

            name = text_array[0].strip(" -")
            sheet = text_array[-1].strip(" ")

            return {"name":name, "sheet":sheet}


    #If we somehow get to the end of this without finding a name and sheet,
    #return the same structure but with None.
    return {"name":None, "sheet":None}




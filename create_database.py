#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
A python script for creating the sqlite database that stores the curling data.
Since the sqlite3 module creates the database if it does not already exist, we
can just go straight into building the tables.
Creates the database file curling_data.db in the current directory.
"""
import database_functions as db


#Start by creating the events table that stores the information about the
#events the curling games are a part of.
#id: ID number of this event, the primary key.
#name: The name of the folder where this event's data was stored (effectively a
#   short name for the event).
#start_date: The start date of this event.
#end_date: The end date of this event.
c = """
CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY,
    name TEXT,
    start_date TEXT,
    end_date TEXT
);
"""
db.run_command(c)

#Now create the games table, which stores information about the individual
#games of the events.
#id: The ID number of this game, the primary key.
#event_id:  The ID number of the event this game is a part of.
#session: The session name from the folder where the shot by shot summary was
#       stored. 
#name: Normally matches the session name (e.g. Gold Medal, Round Robin, etc.),
#       though may contain different information e.g. Group name, if round
#       robin was broken up into groups.
#sheet: The sheet ID the game is being played on.
#type: The kind of game (Currently Men or Women.  Could also add Mixed Doubles,
#   but this project is currently restricting itself to the traditional games).
#start_date: The date of the game in YYYY:MM:DD format.
#start_time: The time the game started in HH:MM (24 hour clock) format.
#team_red: The short name of the red team (e.g. CAN)
#team_yellow: The short name of the yellow team.
#final_score_red: The final score of the red team.
#final_score_yellow:  The final score of the yellow team.
c = """
CREATE TABLE IF NOT EXISTS games(
    id INTEGER PRIMARY KEY,
    event_id INTEGER,
    session TEXT,
    name TEXT,
    sheet TEXT,
    type TEXT,
    start_date TEXT,
    start_time TEXT,
    team_red TEXT,
    team_yellow TEXT,
    final_score_red INTEGER,
    final_score_yellow INTEGER,
        FOREIGN KEY (event_id) REFERENCES events(id)
);
"""
db.run_command(c)

#Now create the table that stores the information about each end in each game.
#id: The ID number of this end, the primary key.
#game_id: The ID number of the game this end is part of.
#number: The number of the end (typically ranges from 1 to 10) in the game.
#direction: Whether playing up or down the sheet (0 for down, 1 for up).
#color_hammer: Color of the team with the hammer (last-rock advantage)
#score_red: The red team's score at the end of this end.
#score_yellow:  The yellow team's score at the end of this end.
#time_left_red:  How much time remains on the red team's clock at the end of this end, in seconds.
#time_left_yellow: How much time remains on the yellow team's clock at the end of this end, in seconds.
c = """
CREATE TABLE IF NOT EXISTS ends(
    id INTEGER PRIMARY KEY,
    game_id INTEGER,
    number INTEGER,
    direction INTEGER,
    color_hammer TEXT,
    score_red INTEGER,
    score_yellow INTEGER,
    time_left_red INTEGER,
    time_left_yellow INTEGER,
        FOREIGN KEY (game_id) REFERENCES games(id)
);

"""
db.run_command(c)

#Now create the table that stores information about each individual shot that
#was taken.
#id: The ID number of the shot, the primary key.
#end_id: The ID number of the end this shot was taken in.
#number: The number of this shot in the end (normally 1 to 16).
#color: The color of the stone being shot (red or yellow).
#team: The short name of the team making the shot.
#player_name: The name of the player taking the shot.
#type: A string categorizing the type of shot being made (e.g. Draw, Take-out,
#   Hit and Roll, etc.
#turn: "In" or "Out" in older games where this terminology was used, or
#   "Clockwise" or "Counter-clockwise" in the later games.  Translating between
#   these conventions requires knowledge of the handedness of the player (for a
#   right-handed player they correspond respectively, for a left-handed player
#   it is the opposite.
#percent_score: The percentage score assigned to each shot.  Ranging from 0% (a
#   complete miss) to 100% (perfectly executed).  Typically just a 4 point
#   scale, but leaving as REAL for flexibility just in case.
c = """
CREATE TABLE IF NOT EXISTS shots(
    id INTEGER PRIMARY KEY,
    end_id INTEGER,
    number INTEGER,
    color TEXT,
    team TEXT,
    player_name TEXT,
    type TEXT,
    turn TEXT,
    percent_score REAL,
        FOREIGN KEY (end_id) REFERENCES ends(id)
);
"""
db.run_command(c)


#Finally, create the table that holds the stone positions after each shot.
#id: The ID number of this stone position.
#shot_id: The ID number of the shot that this stone position follows.
#color:  The color of the stone.
#x:  The x position of this stone, in the "down" coordinate system, with the
#   origin at the button.
#y:  The y position of this stone in the "down" coordinate system, with the
#   origin at the button.
c = """
CREATE TABLE IF NOT EXISTS stone_positions(
    id INTEGER PRIMARY KEY,
    shot_id INTEGER,
    color TEXT,
    x REAL,
    y REAL,
        FOREIGN KEY (shot_id) REFERENCES shots(id)
);
"""
db.run_command(c)

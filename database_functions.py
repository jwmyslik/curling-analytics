#!/usr/bin/env python

# -*- coding: utf-8 -*-
"""
Some helper functions for dealing with the sqlite database.
(With thanks to dataquest.io's "Answering Business Questions using SQL" guided
project).


The database is located at the CADBPATH environment variable.

"""
import sqlite3
import pandas as pd
import os

def run_query(q):
    """
    A function that takes an SQL query as an argument, and returns a pandas
    dataframe with the the result of running that query on the curling_data
    database.
    """
    with sqlite3.connect(os.getenv("CADBPATH")) as conn:
        return pd.read_sql(q, conn)


def run_command(c):
    """
    A function that takes an SQL command as an argument and executes it using
    the sqlite module on the curling_data database.
    """
    with sqlite3.connect(os.getenv("CADBPATH")) as conn:
        conn.isolation_level = None
        conn.execute(c)

def get_next_id(table):
    """
    A function that when given the table name in question, returns the next
    ID number for an entry in that table. (Just equal to the count of elements
    in that table.)
    """
    q = """SELECT COUNT(id) FROM """ + table
    result_df = run_query(q)
    return result_df.iloc[0,0]


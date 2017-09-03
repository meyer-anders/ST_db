#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 29 15:03:40 2017

@author: Anders
"""

import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, ForeignKey, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import backref

from create_schema import Tag, Lesion
from functions import *

engine = create_engine('sqlite:///ST.db')
Base = declarative_base(bind=engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()


# import pattern tables
os.chdir('/Users/Anders/Dropbox/Projects/ST_db_tables')
xl = pd.ExcelFile('EP_age.xlsx')
sheets = xl.sheet_names
for s in sheets:
    table = xl.parse(s, header = None)
    table[0] = table[0].str.lower()
    age_range = table.iloc[0,0]
    lesions = list(table.iloc[1:, 0].dropna())
    for l in lesions:
        lesion = get_or_make_lesion(session, l)
        lesion = add_age(session, lesion, age_range)
        session.commit()
    
session.close()
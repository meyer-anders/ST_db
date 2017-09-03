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

from create_schema import Lesion, Tag, ddx_table
from functions import *

engine = create_engine('sqlite:///ST.db')
Base = declarative_base(bind=engine)
DBSession = sessionmaker(bind=engine, autoflush = False)
session = DBSession()



# import pattern tables
os.chdir('/Users/Anders/Dropbox/Projects/ST_db_tables')
data = pd.read_excel('EP_facts.xlsx', header = None)
data.loc[0,:] = data.loc[0,:].str.lower()
data.loc[1,:] = data.loc[1,:].str.lower()

# fill histogenesis across and take care of gender
ncols = len(data.columns)
n = 1



while n<ncols:
    if not pd.isnull(data.iloc[0, n]):
        histo = data.iloc[0, n]
    else: 
        data.iloc[0, n] = histo
    if data.iloc[4, n] == 'M' or data.iloc[4,n] == 'm':
        data.iloc[4, n] = 1.3
    if data.iloc[4, n] == 'F' or data.iloc[4,n] == 'f':
        data.iloc[4, n] = 0.7
    n += 1

for column in data.iloc[:, 1:]:
    lesion = get_or_make_lesion(session, data.loc[1, column])
    
    lesion.histogenesis = data.loc[0, column]
    
    if not pd.isnull(data.loc[2, column]):
        if float(data.loc[2, column]) >= 1:
            lesion.rel_incidence = data.loc[2,column]
        else: 
            lesion.abs_incidence = data.loc[2, column]
        
    if not pd.isnull(data.loc[3, column]):
        age_ranges = data.loc[3, column].split(', ')
        for age_range in age_ranges:
            lesion = add_age(session, lesion, age_range)
        
    if not pd.isnull(data.loc[4, column]):
        lesion.m_f_ratio = float(data.loc[4,column])
        
    if not pd.isnull(data.loc[5, column]):
        lesion = add_size(session, lesion, data.loc[5,column])
        
    if not pd.isnull(data.loc[6, column]):
        locations = data.loc[6, column].split(',')
        for l in locations:
            tag = get_or_make_tag(session, l)
#            if not tag in lesion.tags:
#                lesion.tags.append(tag)
            get_or_make_assoc(session, tag, lesion)
            session.commit()
    # ddx
    ddx = list(data.loc[7:, column].dropna().drop_duplicates().str.lower())
    for d in ddx:
        ddx_lesion = get_or_make_lesion(session, d)
        lesion.ddxs.append(ddx_lesion)
        session.commit()

session.close()
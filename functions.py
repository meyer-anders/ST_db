#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 29 23:26:03 2017

@author: Anders
"""


import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, ForeignKey, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import backref

from create_schema import Tag, Lesion, Age, Size

def get_or_make_tag(session, tag):
    x = session.query(Tag).filter_by(name = tag)
    if not session.query(x.exists()).scalar():
        new = Tag(name = tag)
        session.add(new)
        session.commit()
        return new
    else: return x.first()
    
def get_or_make_lesion(session, name):
    x = session.query(Lesion).filter_by(name = name)
    if not session.query(x.exists()).scalar():
        new = Lesion(name = name)
        session.add(new)
        session.commit()
        return new
    else: return x.first()

#def get_or_make_assoc(session, tag, lesion):
#    tags = session.query(Lesion.tags).filter(Lesion.id == lesion.id).all()
#    #x = session.query(Association).filter_by(tag = tag).filter_by(lesion = lesion)
#    #if not session.query(x.exists()).scalar():
#    if not tag in tags:
#        lesion.tags.append(tag)
##        new = Association(tag = tag, lesion = lesion)
##        session.add(new)
#        session.commit()
##        return new
##    else: return x.first()
#    return

def load_data(session, tags, table):
    for t in tags:
        tag = get_or_make_tag(session, t)
        for i, r in table.iterrows():
            lesion = get_or_make_lesion(session, r[0].lower())
            if not tag in lesion.tags:
                lesion.tags.append(tag)
            #assoc = get_or_make_assoc(session, tag, lesion)
#            if len(r) > 1:
#                if not pd.isnull(r[1]):
#                    assoc.ppv = r[1]
#                if not pd.isnull(r[2]):
#                    assoc.npv = r[2]        
            session.commit()
    return

def add_age(session, lesion, age_range):
    ages = age_range.split('-')
    ages = [ int(x) for x in ages ]
    new_age = Age(age_range = age_range,
                  age_mean = sum(ages)/2,
                  age_std = (sum(ages)/2)-ages[0])
    session.add(new_age)
    lesion.tags.append(new_age)
#    session.commit()
#    new = Association(tag = new_age, lesion = lesion)
#    session.add(new)
    session.commit()
    return lesion

def add_size(session, lesion, size_range):
    sizes = size_range.split('-')
    sizes = [ int(x) for x in sizes ]
    new_size = Size(size_range = size_range,
                  size_mean = sum(sizes)/2,
                  size_std = (sum(sizes)/2)-sizes[0])
    session.add(new_size)
    lesion.tags.append(new_size)
    session.commit()
#    new = Association(tag = new_size, lesion = lesion)
#    session.add(new)
#    session.commit()
    return lesion

def combine(a, b):
    if a == None: return b
    else: return a
    

def merge_lesions(session, keep, drop):
    for i in ['histogenesis', 'm_f_ratio', 'rel_incidence', 'abs_incidence']:
        x = combine(getattr(keep, i), getattr(drop, i))
        setattr(drop, i, x)
    for t in drop.tags:
        keep = get_or_make_assoc(session, t, keep)
    session.remove(drop)
    session.commit()
    return
        

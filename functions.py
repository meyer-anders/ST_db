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

from create_schema import Tag, Lesion, Age, Size, Association
import pandas as pd
from scipy.stats import truncnorm
import difflib
from difflib import SequenceMatcher

engine = create_engine('sqlite:///ST.db')
Base = declarative_base(bind=engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()

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

def get_or_make_assoc(session, tag, lesion):
    x = session.query(Association).filter(Association.tag_id==tag.id, 
                                         Association.lesion_id == lesion.id)
    if not session.query(x.exists()).scalar():
        new = Association(tag = tag, lesion = lesion)
        session.add(new)
        session.commit()
    return
    
def load_data(session, tags, table):
    for t in tags:
        tag = get_or_make_tag(session, t)
        for i, r in table.iterrows():
            lesion = get_or_make_lesion(session, r[0].lower())
            get_or_make_assoc(session, tag, lesion)
    return

def add_age(session, lesion, age_range):
    ages = age_range.split('-')
    ages = [ int(x) for x in ages ]
    x = session.query(Age).filter_by(age_range = age_range)
    if not session.query(x.exists()).scalar():
        new_age = Age(age_range = age_range,
                      age_mean = sum(ages)/2,
                      age_std = (sum(ages)/2)-ages[0])
        session.add(new_age)
        session.commit()
        get_or_make_assoc(session, new_age, lesion)
    else:
        get_or_make_assoc(session, x[0], lesion)
    session.commit()
    return lesion

def add_size(session, lesion, size_range):
    sizes = size_range.split('-')
    sizes = [ int(x) for x in sizes ]
    new_size = Size(size_range = size_range,
                  size_mean = sum(sizes)/2,
                  size_std = (sum(sizes)/2)-sizes[0])
    session.add(new_size)
    session.commit()
    get_or_make_assoc(session, new_size, lesion)
    session.commit()
    return lesion

def combine(a, b):
    if a == None: return b
    else: return a
    

def merge_lesions(session, keep, drop):
    for i in ['histogenesis', 'm_f_ratio', 'rel_incidence', 'abs_incidence']:
        x = combine(getattr(keep, i), getattr(drop, i))
        setattr(drop, i, x)
    for t in drop.tags:
        get_or_make_assoc(session, t.tag, keep)
    for d in drop.ddxs:
        if not d in keep.ddxs:
            keep.ddxs.append(d)
    session.delete(drop)
    session.commit()
    return

def merge_lesions_on_id(session, k_id, d_id):
    k = session.query(Lesion).filter_by(id = k_id)[0]
    d = session.query(Lesion).filter_by(id = d_id)[0]
    merge_lesions(session, k, d)
    return

def merge_mult_lesions(session, lesion_ids):
    n = len(lesion_ids)
    for l in range(1, n):
        merge_lesions(session, l[0], l[i])
    return

def calc_ppv(x, mu, sigma):
    lower, upper = 0, 100
    a = (lower - mu) / sigma
    b = (upper - mu) / sigma
    cdf = truncnorm.cdf(x, a, b, mu, sigma)
    return 1 + cdf/(1-cdf)
    

def get_prob_age(session, lesion_id, age):
    l = session.query(Lesion, Age, Association).filter(Lesion.id ==lesion_id, 
                       Association.lesion_id == Lesion.id, 
                       Association.tag_id == Tag.id)
    if session.query(x.exists()).scalar():
        return calc_ppv(age, l[0].age_mean, l[0].age_std)
    else:
        return 1

def get_prob_size(session, lesion_id, size):
    l = session.query(Lesion, Size, Association).filter(Lesion.id ==lesion_id, 
                       Association.lesion_id == Lesion.id, 
                       Association.tag_id == Tag.id)
    if session.query(x.exists()).scalar():
        return calc_ppv(size, l[0].size_mean, l[0].size_std)
    else:
        return 1

def get_lesions(session, tags):
    data = session.query(Lesion, Tag, Association).\
            filter(Association.lesion_id == Lesion.id,
                   Association.tag_id == Tag.id,
                   Tag.name.in_(tags))
    data_df = pd.read_sql(data.statement.apply_labels(), engine)
    lesions = data_df.drop_duplicates(subset = 'lesion_id')
    final = lesions[['lesion_id', 'lesion_abs_incidence']].\
                    set_index(keys = 'lesion_id', drop = True).\
                    sort_values(by='lesion_abs_incidence', ascending = False)
    final['post'] = final['lesion_abs_incidence']
    for t in tags:
        l_w_t = data_df.loc[data_df.tag_name == t, :]
        final[t] = 0.75
        for i in final.index:
            combo = l_w_t.loc[l_w_t.lesion_id == i]
            if len(combo)>0:
                u = int(combo.association_upvotes)
                d = int(combo.association_downvotes)
                if (u+d) == 0: ppv = 1
                else: ppv = ((u-d)/(u+d)) + 1
                final.set_value(i, t, ppv)
            probs = final.loc[i, :]
            probs = probs.drop('post')
            final.set_value(i, 'post', probs.product())
        
    return final.sort_values(by='post', ascending = False)




def set_abs_incidence(session):
    lesions = session.query(Lesion).all()
    for l in lesions:
        if l.abs_incidence == None:
            l.abs_incidence = l.rel_incidence**3/10000
    session.commit()
    return

# not working yet
def highlight_dups(session):
    names = session.query(Lesion.id, Lesion.name)
    names = pd.read_sql(names.statement, engine)
    n = len(names)
    for i in range(n):
        for j in range(n):
            
            s = SequenceMatcher(None, names.loc[i,'name'], names.loc[j, 'name']).ratio()
            if s > 0.5:
                b = input("{} \n {}:\n ".format(names.loc[i,'name'], 
                          names.loc[j, 'name']))
                if b == 'y':
                    merge_lesions_on_id(session, names.loc[i, 'id'], names.loc[j, 'id'])
    return
    

    
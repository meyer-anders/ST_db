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
from scipy.stats import norm
import difflib
from difflib import SequenceMatcher

engine = create_engine('sqlite:///ST.db')
Base = declarative_base(bind=engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()

def get_or_make_tag(session, tag_name):
    x = session.query(Tag).filter_by(name = tag_name)
    if not session.query(x.exists()).scalar():
        new = Tag(name = tag_name)
        session.add(new)
        session.commit()
        return new
    else: 
        return x.first()
    
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
    else:
        x.first().upvotes += 1
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
        session.delete(t)
        session.commit()
    for d in drop.ddxs:
        if not d in keep.ddxs:
            keep.ddxs.append(d)
            drop.ddxs.remove(d)
    is_ddx = session.query(Lesion).filter(Lesion.ddxs.contains(drop)).all()
    for d in is_ddx:
        d.ddxs.append(drop)
    session.delete(drop)
    session.commit()
    return

def merge_tags(session, keep, drop):
    for c in drop.containers:
        keep.containers.append(c)
        drop.containers.remove(c)    
    for l in drop.lesions:
        get_or_make_assoc(session, drop, l.lesion)
        session.delete(l)
        session.commit()
    is_container = session.query(Tag).filter(Tag.containers.contains(drop)).all()
    for c in is_container:
        c.containers.append(drop)
    session.delete(drop)
    session.commit()
    return

def merge_tags_on_id(session, k_id, d_id):
    k = session.query(Tag).filter_by(id = k_id).first()
    d = session.query(Tag).filter_by(id = d_id).first()
    merge_tags(session, k, d)
    return

def get(session, Class, n):
    l = session.query(Class).filter_by(id = n).first()
    print (l.name)
    return l

def merge_lesions_on_id(session, k_id, d_id):
    k = session.query(Lesion).filter_by(id = k_id).first()
    d = session.query(Lesion).filter_by(id = d_id).first()
    merge_lesions(session, k, d)
    return

def m (session):
    while True:
        k = input("keep: ")
        if k != 'q':
            d = input("drop: ")
            merge_lesions_on_id(session, k, d)
        else: break
    return

def merge_mult_lesions(session, lesion_ids):
    n = len(lesion_ids)
    for l in range(1, n):
        merge_lesions_on_id(session, l[0], l[i])
    return

def calc_ppv(x, mu, sigma):
    lower, upper = 0, 100
    a = (lower - mu) / sigma
    b = (upper - mu) / sigma
    cdf = norm.cdf(x, mu, sigma)
    if x < mu: return 0.5 + cdf/(1-cdf)
    else: return 0.5 +(1-cdf)/cdf
    

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

def add_age_prob(session, age, magnifier, final):
    data = session.query(Lesion, Age, Association).\
            filter(Association.lesion_id == Lesion.id,
                   Association.tag_id == Tag.id)
    data_df = pd.read_sql(data.statement.apply_labels(), engine)
    data_df['delta']= abs(data_df['tag_age_mean']-age)
    final['age'] = 1/magnifier
    for i in final.index:
        age_range = data_df.loc[data_df.lesion_id == i, :]
        prob = 1
        if len(age_range) >0:
            age_range = age_range.sort_values(by='delta').\
                        reset_index(drop=True).iloc[0,:]
            prob = calc_ppv(age, age_range.tag_age_mean,
                                    age_range.tag_age_std)
            u = int(age_range.association_upvotes)
            d = int(age_range.association_downvotes)
            if (u+d) == 0: ppv = 1
            else: ppv = ((u-d)/(u+d)) * magnifier
            if prob >=1: prob = prob * ppv
            else: prob = prob / ppv
        final.set_value(i, 'age', prob)
    return final
        
def add_size_prob(session, size, magnifier, final):
    data = session.query(Lesion, Size, Association).\
            filter(Association.lesion_id == Lesion.id,
                   Association.tag_id == Tag.id)
    data_df = pd.read_sql(data.statement.apply_labels(), engine)
    data_df['delta']= abs(data_df['tag_size_mean']-size)
    final['size'] = 1/magnifier
    for i in final.index:
        size_range = data_df.loc[data_df.lesion_id == i, :]
        prob = 1
        if len(size_range)>0:
            size_range = size_range.sort_values(by= 'delta').\
                        reset_index(drop=True).iloc[0,:]
            prob = calc_ppv(size, size_range.tag_size_mean,
                                    size_range.tag_size_std)
            u = int(size_range.association_upvotes)
            d = int(size_range.association_downvotes)
            if (u+d) == 0: ppv = 1
            else: ppv = ((u-d)/(u+d)) * magnifier
            if prob >=1: prob = prob * ppv
            else: prob = prob / ppv
        final.set_value(i, 'size', prob)
    return final     
    
    
    
def get_lesions(session, tags, 
                age= None, age_m = 2, 
                size= None, size_m = 2): #tags ={tag: magnifier}
    data = session.query(Lesion, Tag, Association).\
            filter(Association.lesion_id == Lesion.id,
                   Association.tag_id == Tag.id)
    data_df = pd.read_sql(data.statement.apply_labels(), engine)
    lesions = data_df.drop_duplicates(subset = 'lesion_id')
    final = lesions[['lesion_id', 'lesion_name', 'lesion_abs_incidence']].\
                    set_index(keys = 'lesion_id', drop = True).\
                    sort_values(by='lesion_abs_incidence', ascending = False)
    final['post'] = final['lesion_abs_incidence']
    for t, m in tags.items():
        l_w_t = data_df.loc[data_df.tag_name == t, :]
        final[t] = 1.0/m #ppv if tag is not found
        for i in final.index:
            combo = l_w_t.loc[l_w_t.lesion_id == i]
            if len(combo)>0:
                u = int(combo.association_upvotes)
                d = int(combo.association_downvotes)
                if (u+d) == 0: ppv = 1
                else: ppv = ((u-d)/(u+d)) * m
                final.set_value(i, t, ppv)
    if age != None:
        final = add_age_prob(session, age, age_m, final)
    if size != None:
        final = add_size_prob(session, size, size_m, final)
    for i in final.index:
        probs = final.loc[i, :]
        probs = probs.drop(['post', 'lesion_name'])
        final.set_value(i, 'post', probs.product())
    
    
    
#    data_df = data_df.drop_duplicates(subset= 'lesion_id').\
#                set_index(keys = 'lesion_id', drop = True)
    #return pd.merge(final, data_df, how = "inner", left_index = True,
     #               right_index = True).sort_values(by='post', ascending = False)

    return final.sort_values(by='post', ascending = False) 
        


def def_container_tag(session, tag_name, container_name, update_lesions = False):
    tag = get_or_make_tag(session, tag_name)
    container = get_or_make_tag(session, container_name)
    if not container in tag.containers:
        tag.containers.append(container)
        session.commit()
    if update_lesions:
        lesions = session.query(Lesion).join(Association).\
                filter(Association.lesion_id == Lesion.id,
                       Association.tag_id == Tag.id,
                       Association.tag == tag).all()
        for l in lesions:
            get_or_make_assoc(session, container, l)
    session.commit()
    return

def make_containers(session):
    tags = session.query(Tag).all()
    for t in tags:
        if t.name != None:
            print ('{}, {}'.format(t.name, t.id))
            for c in t.containers:
                print (c.name)
            a = input("add? ")
            if a == 'y':
                b = input(">")
                def_container_tag(session, t.name, b, True)
                
            else: 
                if a == 'q':
                    break
    return
    

def see_tag_containers(session):
    tags = session.query(Tag).all()
    df = pd.DataFrame()
    for t in tags:
        if t.name != None:
            temp = pd.DataFrame({t.name: pd.Series([c.name for c in t.containers])})
            df = pd.concat([temp, df], axis = 1)
    return df

def contain_mult_tags(session, container_name, tags, update_lesions = False):
    for t in tags:
        def_container_tag(session, t, container_name, update_lesions)
    return


def upvote_ddx(session, x):
    for l in x.ddxs:
        for a in x.tags:
            q = session.query(Association).filter_by(lesion = l, tag = a.tag)
            if session.query(q.exists()).scalar():
                assoc = q.first()
                assoc.upvotes += 1
            else:
                new = Association(lesion = l, tag = a.tag)
                session.add(new)
            session.commit()
    return

def process_ddx(session):
    lesions = session.query(Lesion).all()
    for l in lesions:
        upvote_ddx(session, l)
    return
    
def set_abs_incidence(session):
    lesions = session.query(Lesion).all()
    for l in lesions:
        if l.abs_incidence == None:
            l.abs_incidence = l.rel_incidence**3/10000
    session.commit()
    return


def highlight_dups(session, cutoff):
    names = session.query(Lesion.id, Lesion.name)
    names = pd.read_sql(names.statement, engine)
    n = len(names)
    #matches = pd.DataFrame(columns = ['ratio', 'a_name', 'b_name', 'a_id', 'b_id'])
    dicts = []
    for i in range(n):
        for j in range(i, n):
            if i != j:
                s = SequenceMatcher(None, names.loc[i,'name'], names.loc[j, 'name']).ratio()
                if s > cutoff:
                    temp = {'ratio': s,
                            'a_name': names.loc[i,'name'],
                            'b_name' : names.loc[j,'name'],
                            'a_id' : names.loc[i,'id'],
                            'b_id' : names.loc[j,'id']}
                    dicts.append(temp)
    matches = pd.DataFrame()
    return matches.from_dict(dicts).sort_values(by='ratio', ascending = False)
    

    
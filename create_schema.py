#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 29 15:16:53 2017

@author: Anders
"""

from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, ForeignKey, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session, with_polymorphic
from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declared_attr




engine = create_engine('sqlite:///ST.db')
Base = declarative_base(bind=engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()


ddx_table = Table("ddx_table", Base.metadata,
    Column("main_dx_id", Integer, ForeignKey("lesion.id"), primary_key=True),
    Column("ddx_lesion_id", Integer, ForeignKey("lesion.id"), primary_key=True)
)

tag_table = Table("tag_table", Base.metadata,
    Column("inner_tag_id", Integer, ForeignKey("tag.id"), primary_key=True),
    Column("container_tag_id", Integer, ForeignKey("tag.id"), primary_key=True)
)
#
#association_table = Table("association_table", Base.metadata,
#     Column("lesion_id", Integer, ForeignKey("lesion.id"), primary_key = True),
#     Column("tag_id", Integer, ForeignKey("tag.id"), primary_key = True)
#)


class Association(Base):
    __tablename__ = 'association'
    lesion_id = Column(Integer, ForeignKey('lesion.id'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tag.id'), primary_key=True)
    upvotes = Column(Integer, default = 10)
    downvotes = Column(Integer, default = 5)
    lesion = relationship("Lesion", back_populates="tags")
    tag = relationship("Tag", back_populates="lesions")



    
class Lesion(Base):
    __tablename__ = "lesion"
    id = Column(Integer, primary_key = True)
    name = Column(String(250))
    # static facts
    histogenesis = Column(String(50))
    m_f_ratio = Column(Float, default = 1.0)
    rel_incidence = Column(Integer, default = 2)
    abs_incidence = Column(Float)
    # modifiable

    tags = relationship("Association", back_populates = "lesion")

    ddxs = relationship("Lesion",
                        secondary = ddx_table,
                        primaryjoin=id==ddx_table.c.main_dx_id,
                        secondaryjoin=id==ddx_table.c.ddx_lesion_id)              

class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
#    lesions = relationship("Lesion",
#                           secondary = association_table,
#                           backref = "tags",
#                           lazy = "dynamic")
    
    lesions = relationship("Association", back_populates = "tag")
    discriminator = Column('type', String(50))
    containers = relationship("Tag",
                              secondary = tag_table,
                              primaryjoin=id==tag_table.c.inner_tag_id,
                              secondaryjoin=id==tag_table.c.container_tag_id,
                              backref = "inner_tags")
    __mapper_args__ = {'polymorphic_on': discriminator}

class Age(Tag):
    __mapper_args__ = {'polymorphic_identity': 'age'}
    age_range = Column(String(50))
    age_mean = Column(Float)
    age_std = Column(Float)

class Size(Tag):
    __mapper_args__ = {'polymorphic_identity': 'size'}
    size_range = Column(String(50))
    size_mean = Column(Float)
    size_std = Column(Float)
    

Base.metadata.create_all()
session.close()


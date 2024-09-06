from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, BigInteger
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Organisation(Base):
    __tablename__ = 'organisation'

    id = Column(Integer, primary_key=True)
    name = Column(String(199), nullable=False)
    status = Column(Integer, default=0, nullable=False)
    personal = Column(Boolean, default=False, nullable=True)
    settings = Column(JSON, default={}, nullable=True)
    created_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=True)

    members = relationship('Member', back_populates='organisation')
    roles = relationship('Role', back_populates='organisation')


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(199), unique=True, nullable=False)
    password = Column(String(199), nullable=False)
    profile = Column(JSON, default={}, nullable=False)
    status = Column(Integer, default=0, nullable=False)
    settings = Column(JSON, default={}, nullable=True)
    created_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=True)

    members = relationship('Member', back_populates='user')


class Member(Base):
    __tablename__ = 'member'

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey('organisation.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('role.id', ondelete='CASCADE'), nullable=False)
    status = Column(Integer, nullable=False, default=0)
    settings = Column(JSON, default={}, nullable=True)
    created_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=True)

    organisation = relationship('Organisation', back_populates='members')
    user = relationship('User', back_populates='members')
    role = relationship('Role', back_populates='members')


class Role(Base):
    __tablename__ = 'role'

    id = Column(Integer, primary_key=True)
    name = Column(String(199), nullable=False)
    description = Column(String(199), nullable=True)
    org_id = Column(Integer, ForeignKey('organisation.id', ondelete='CASCADE'), nullable=False)

    organisation = relationship('Organisation', back_populates='roles')
    members = relationship('Member', back_populates='role')

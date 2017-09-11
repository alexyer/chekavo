from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    start_date = Column(DateTime, index=True)

    applications = relationship('Application', back_populates='event')


class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    event_id = Column(Integer, ForeignKey('events.id'))

    event = relationship('Event', back_populates='applications')

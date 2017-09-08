import os
import re

import facebook
import logging
from sqlalchemy import create_engine, exists
from sqlalchemy.orm import sessionmaker, scoped_session
from telegram.ext import Updater, MessageHandler, Filters

from models import Base, Event

graph = facebook.GraphAPI(access_token=os.environ['CHEKAVO_FB_TOKEN'])
engine = create_engine(os.environ['CHEKAVO_DB'])

Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine))


logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)


def parse_event(bot, update):
    try:
        event_id = re.search(r'.*facebook\.com/events/(\d+)/.*',
                             update.message.text).group(1)
    except:
        return

    event = graph.get_object(id=event_id, fields='name,start_time')

    session = Session()

    if not session.query(exists().where(Event.name == event['name'])).scalar():
        new_event = Event(name=event['name'],
                          start_date=event['start_time'],
                          url=update.message.text)
        session.add(new_event)
        session.commit()

        bot.send_message(chat_id=update.message.chat_id,
                         text='New event: [{}]({}), id: {}'.format(new_event.name,
                                                                   new_event.url,
                                                                   new_event.id),
                         parse_mode='Markdown')


def main():
    try:
        token = os.environ['CHEKAVO_TOKEN']
    except:
        raise AttributeError('Provide bot token')

    updater = Updater(token=token)
    dispatcher = updater.dispatcher

    parse_event_handler = MessageHandler(Filters.text, parse_event)
    dispatcher.add_handler(parse_event_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()

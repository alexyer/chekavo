import os
import re
from datetime import datetime

import facebook
import logging
from sqlalchemy import create_engine, exists
from sqlalchemy.orm import sessionmaker, scoped_session
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

from models import Base, Event, Application

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
                         text='New event: [{}]({}), id: {}'.format(
                             new_event.name,
                             new_event.url,
                             new_event.id),
                         parse_mode='Markdown')


def upcoming(bot, update):
    session = Session()
    upcoming_events = ('{}: [{}]({}) at {}'.format(e.id,
                                                   e.name,
                                                   e.url,
                                                   e.start_date.strftime('%b %d %a %H:%M'))
                       for e in session.query(Event).
                           filter(Event.start_date >= datetime.now()).
                           order_by(Event.start_date))

    bot.send_message(chat_id=update.message.chat_id,
                     text='Upcoming events:\n{}'.format('\n'.join(upcoming_events)),
                     parse_mode='Markdown')


def apply(bot, update, args):
    session = Session()
    event = _get_event(args, session)
    username = update.message.from_user.username

    if not session.query(exists().where(Application.event_id == event.id).
                                  where(Application.username == username)).scalar():
        new_application = Application(event_id=event.id, username=username)
        session.add(new_application)
        session.commit()

        bot.send_message(chat_id=update.message.chat_id,
                         text='@{} is going to [{}]({})'.format(username,
                                                                event.name,
                                                                event.url),
                         parse_mode='Markdown')


def _get_event(args, session):
    return session.query(Event).filter(Event.id == args[0]).first()


def who(bot, update, args):
    session = Session()
    event = _get_event(args, session)
    people = ('@{}'.format(a.username) for a in event.applications)
    bot.send_message(chat_id=update.message.chat_id,
                     text='[{}]({}):\n{}'.format(event.name, event.url,
                                                 '\n'.join(people)),
                     parse_mode='Markdown')


def bail(bot, update, args):
    session = Session()
    event = _get_event(args, session)
    username = update.message.from_user.username
    session.query(Application).filter(Application.event_id == event.id,
                                      Application.username == username).delete()
    bot.send_message(chat_id=update.message.chat_id,
                     text='@{} is not going to [{}]({})'.format(username,
                                                                event.name,
                                                                event.url),
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

    upcoming_handler = CommandHandler('upcoming', upcoming)
    dispatcher.add_handler(upcoming_handler)

    apply_handler = CommandHandler('apply', apply, pass_args=True)
    dispatcher.add_handler(apply_handler)

    who_handler = CommandHandler('who', who, pass_args=True)
    dispatcher.add_handler(who_handler)

    bail_handler = CommandHandler('bail', bail, pass_args=True)
    dispatcher.add_handler(bail_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()

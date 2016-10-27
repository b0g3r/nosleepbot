import logging
import telepot
from sys import argv
from datetime import datetime, timedelta
import time
import os
from scheduler import Scheduler
from threading import Thread
from model import User, Delay, State, db_proxy
from flask import Flask, request, Response, g
from peewee import fn


scheduler = Scheduler()

app = Flask('nosleepbot')

token = os.environ['TOKEN_BOT']
bot = telepot.Bot(token)

# TODO: url_for
url = os.environ.get('URL')

# TODO: create a set of phrases
# TODO: create a decorator for schedule-events
# TODO: просмотр рандомного пользователя онлайн

# TODO: refactor this
attempts = 10

@app.before_request
def before_request():
    g.db = db_proxy
    g.db.connect()


@app.after_request
def after_request(response):
    g.db.close()
    return response


def restart_users_event():
    for user in User.select().where(User.state != State.stop):
        delta = (datetime.now() - user.time).seconds
        if user.state == State.start and delta < Delay.check:
            scheduler.set_event(user, Delay.check - delta, check, {'user': user})
        elif user.state == State.wait_resp and delta < Delay.alarm:
            scheduler.set_event(user, Delay.alarm - delta, wakeup, {'user': user})
        elif user.state == State.wake_up and delta < attempts*Delay.wake_up:
            scheduler.set_event(user, Delay.wake_up - delta, wakeup, {'user': user})

        else:
            user.send_message(("Мы обновляли проект и у нас произошла ошибка"
                                                ":( Тебе придется начать заново"))
            user.state = State.stop
            user.save()


def check(user):
    user.send_message("Ты спишь? А?")
    user.state = State.wait_resp
    user.time = datetime.now()
    scheduler.set_event(user, Delay.alarm, wakeup, {'user': user})
    user.save()


def wakeup(user):
    user.send_message("Ты что, уснула?")
    if (datetime.now() - user.time).seconds < attempts*Delay.wake_up:
        user.state = State.wake_up
        user.save()
        scheduler.set_event(user, Delay.wake_up, wakeup, kwargs={'user': user})
    else:
        user.state = State.stop
        user.save()
        app.logger.info('%s %s %s', datetime.now(), user.user_id, 'уснул')


def start(user):
    user.send_message("Напишу тебе через 20 минут!")
    user.state = State.start
    user.time = datetime.now()
    scheduler.set_event(user, Delay.check, check, kwargs={'user': user})
    user.save()


def stop(user):
    user.send_message("Теперь можешь ложиться спать")
    user.state = State.stop
    user.time = datetime.now()
    user.messages = ''
    scheduler.cancel_event(user)
    app.logger.info('%s %s %s', datetime.now(), user.user_id, 'ушел спать')
    user.save()


def handle(message):
    content_type, chat_type, user_id = telepot.glance(message)
    app.logger.info('%s %s', message['chat']['first_name'], message['text'])
    user, _ = User.get_or_create(user_id=str(user_id))
    user.messages += 'соня: %s\n' % message['text']
    if '/start' in message['text']:
        start(user)
    elif '/stop' in message['text']:
        stop(user)
    else:
        if user.state == State.wait_resp or user.state == State.wake_up:
            user.send_message("Смотри мне!")
            scheduler.cancel_event(user)
            start(user)


@app.route('/messages', methods=['POST'])
def get_messages():
    id = request.form['id']
    messages = User.get(User.id == id).messages
    print(messages)
    return '123'

@app.route('/')
def index():
    #TODO: сделать темплейт с ajaxom в messages
    q = User.select().where(User.state != State.stop).order_by(fn.Random()).get()
    print(q.user_id)
    print(type(q))
    return q.user_id


@app.route('/webhook/%s' % token, methods=['POST'])
def webhook_get_updates():
    json = request.get_json(cache=False)
    if json is not None:
        handle(json['message'])
    return Response(status=200)


def init():
    if 'HEROKU' in os.environ:
        app.logger.addHandler(logging.StreamHandler())
        webhook_url = '%s/%s/%s' % (url, 'webhook', token)
        if webhook_url != bot.getWebhookInfo()['url']:
            bot.setWebhook(webhook_url)
    elif 'LOCAL' in os.environ:
        bot.setWebhook('')
        bot.message_loop(handle, relax=0.3, timeout=10)
        app.logger.addHandler(logging.StreamHandler())

    #restart_users_event()

    scheduler.run()

    if 'DEBUG' in os.environ:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.INFO)
    app.logger.info('app started')

init()
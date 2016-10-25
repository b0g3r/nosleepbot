import logging
import telepot
import sched
from sys import argv
from datetime import datetime
import time
import os
from threading import Thread
from model import User, Delay, State, db_proxy
from flask import Flask, request, Response, g


app = Flask('nosleepbot')
events = {}
scheduler = sched.scheduler(time.time, time.sleep)
token = '246227695:AAG1KJzBGfJeQqoeWXXvRp86VnjI1V29Q7g'
bot = telepot.Bot(token)
# TODO: url_for
url = 'https://nosleep-bot-staging.herokuapp.com'

# TODO: logging
# TODO: create a set of phrases
# TODO: flask and webhook
# TODO: create a decorator for schedule-events


@app.before_request
def before_request():
    g.db = db_proxy
    g.db.connect()


@app.after_request
def after_request(response):
    g.db.close()
    return response

def cancel_event(user):
    if user.user_id in events:
        event = events.get(user.user_id)
        if event in scheduler.queue:
            scheduler.cancel(event)


def set_event(user, event):
    cancel_event(user)
    events[user.user_id] = event


def run_pending():
    while 1:
        scheduler.run(blocking=False)
        time.sleep(1)
        app.logger.debug(str(scheduler.queue))

def restart_users_event():
    for user in User.select().where(User.state != State.stop):
        bot.sendMessage(user.user_id, "У нас тут произошла какая-то ошибка, поэтому давай начнем всё сначала")
        start(user)


def check(user):
    bot.sendMessage(user.user_id, text="Ты спишь? А?")
    user.state = State.wait_resp
    user.time = datetime.now()
    set_event(user, scheduler.enter(Delay.alarm, 1, wakeup, kwargs={'user': user}))  # 60
    user.save()


def wakeup(user):
    bot.sendMessage(user.user_id, text="Ты что, уснула?")
    if (datetime.now() - user.time).seconds < 1200:
        set_event(user, scheduler.enter(Delay.wake_up, 1, wakeup, kwargs={'user': user}))  # 60
    else:
        user.state = State.stop
        user.save()
        app.logger.info('%s %s %s', datetime.now(), user.user_id, 'уснул')


def start(user):
    bot.sendMessage(user.user_id, "Напишу тебе через 20 минут!")
    user.state = State.start
    user.time = datetime.now()
    set_event(user, scheduler.enter(Delay.check, 1, check, kwargs={'user': user}))  # 1200
    user.save()


def stop(user):
    bot.sendMessage(user.user_id, "Теперь можешь ложиться спать")
    user.state = State.stop
    user.time = datetime.now()
    cancel_event(user)
    app.logger.info('%s %s %s', datetime.now(), user.user_id, 'ушел спать')
    user.save()


def handle(message):
    content_type, chat_type, user_id = telepot.glance(message)
    app.logger.info('%s %s', message['chat']['first_name'], message['text'])
    try:
        user = User.get(User.user_id == str(user_id))
    except User.DoesNotExist:
        user = User.create(user_id=str(user_id))

    if '/start' in message['text']:
        start(user)
    elif '/stop' in message['text']:
        stop(user)
    else:
        if user.state == State.wait_resp or user.state == State.wake_up:
            bot.sendMessage(user.user_id, "Смотри мне!")
            cancel_event(user)
            start(user)


@app.route('/')
def index():
    return 'hello world'


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
        print(bot.getWebhookInfo(), webhook_url, bot.getWebhookInfo()['url'])
        if webhook_url != bot.getWebhookInfo()['url']:
            bot.setWebhook(webhook_url)


    elif 'LOCAL' in os.environ:
        bot.setWebhook('')
        bot.message_loop(handle, relax=0.3, timeout=10)
        app.logger.addHandler(logging.StreamHandler())

    restart_users_event()

    t = Thread(target=run_pending)
    t.start()

    app.logger.setLevel(logging.INFO)
    app.logger.info('app started')
init()

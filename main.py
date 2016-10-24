import logging
import telepot
import sched
from sys import argv
from datetime import datetime
import time
from peewee import Model, SqliteDatabase, CharField, DateField, SmallIntegerField
import os
from threading import Thread
from flask import Flask, request, url_for, Response

app = Flask('nosleepbot')
events = {}
scheduler = sched.scheduler(time.time, time.sleep)
token = '246227695:AAG1KJzBGfJeQqoeWXXvRp86VnjI1V29Q7g'
bot = telepot.Bot(token)
db = SqliteDatabase('users.db')
url = 'https://nosleepbot.pythonanywhere.com'

# TODO: logging
# TODO: create a set of phrases
# TODO: flask and webhook

class Delay:
    check = 10  # 1200
    alarm = 10  # 60
    wake_up = 10  # 60


class State:
    stop = 0
    start = 1
    wait_resp = 2
    wake_up = 3


class User(Model):
    user_id = CharField(unique=True)
    time = DateField(null=True)
    state = SmallIntegerField(null=True)

    class Meta:
        database = db


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
    db.connect()
    db.create_tables([User], safe=True)
    db.close()
    if os.environ.get('LOCAL') != 'YES':
        import urllib3
        proxy_url = 'http://proxy.server:3128'
        telepot.api._pools = {
            'default': urllib3.ProxyManager(proxy_url=proxy_url, num_pools=3, maxsize=10, retries=False, timeout=30),
        }
        telepot.api._onetime_pool_spec = (
            urllib3.ProxyManager, dict(proxy_url=proxy_url, num_pools=1, maxsize=1, retries=False, timeout=30)
        )
        bot.setWebhook('%s/%s/%s' % (url, 'webhook', token))
    else:
        bot.setWebhook('')
        bot.message_loop(handle, relax=0.1, timeout=10)
        app.logger.addHandler(logging.StreamHandler())

    restart_users_event()

    t = Thread(target=run_pending)
    t.start()

    app.logger.setLevel(logging.DEBUG)
    app.logger.info('app started')


init()

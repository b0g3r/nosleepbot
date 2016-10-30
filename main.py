import logging
import telepot
from datetime import datetime
import os
from scheduler import Scheduler
from model import User, Delay, State, db_proxy
from flask import Flask, request, Response, g, render_template, url_for
from peewee import fn


scheduler = Scheduler()

app = Flask('nosleepbot')

token = os.environ['TOKEN_BOT']
bot = telepot.Bot(token)

# TODO: migrations

# TODO: create a set of phrases
# TODO: create a decorator for schedule-events

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
            scheduler.set_event(user, check, Delay.check - delta)
        elif user.state == State.wait_resp and delta < Delay.alarm:
            scheduler.set_event(user, wakeup, Delay.alarm - delta)
        elif user.state == State.wake_up and delta < attempts*Delay.wake_up:
            scheduler.set_event(user, wakeup, Delay.wake_up - delta)

        else:
            user.send_message("Мы обновляли проект и у нас произошла не очень страшная ошибка"
                              ", но тебе придется начать заново: /start")
            user.state = State.stop
            user.save()


def check(user):
    user.send_message("Ты спишь? А?")
    user.state = State.wait_resp
    user.time = datetime.now()
    scheduler.set_event(user, wakeup, Delay.alarm)
    user.save()


def wakeup(user):
    user.send_message("Ты что, уснула?")
    if (datetime.now() - user.time).seconds < attempts*Delay.wake_up:
        user.state = State.wake_up
        user.save()
        scheduler.set_event(user, wakeup, Delay.wake_up)
    else:
        user.state = State.stop
        user.save()
        app.logger.info('%s %s %s', datetime.now(), user.user_id, 'уснул')


def start(user):
    user.send_message("Напишу тебе через 20 минут!")
    user.state = State.start
    user.time = datetime.now()
    scheduler.set_event(user, check, Delay.check)
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
    user, _ = User.get_or_create(defaults={'scheduler':scheduler}, user_id=str(user_id))
    user.messages += 'соня: %s\n' % message['text']
    user.save()
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
    return messages


# TODO: Запилить "Пользователь ушел спать" (пусть /messages возвращает ошибку 404, а ajax это отлавливает?)
# TODO: Запилить красивую верстку
@app.route('/')
def index():
    q = User.select().where(User.state != State.stop)
    if q.exists():
        return render_template('index.html', user_id=q.order_by(fn.Random()).get().id)
    else:
        return "Сичас никого нет"

# TODO: maybe replace token to secret_key?
@app.route('/webhook/%s' % token, methods=['POST'])
def webhook_get_updates():
    json = request.get_json(cache=False)
    if json is not None:
        handle(json['message'])
    return Response(status=200)


def init():
    if 'HEROKU' in os.environ:
        app.logger.addHandler(logging.StreamHandler())
        webhook_url = 'https://%s/%s/%s' % (os.environ['URL'], 'webhook', token)
        if webhook_url != bot.getWebhookInfo()['url']:
            bot.setWebhook(webhook_url)
    elif 'LOCAL' in os.environ:
        bot.setWebhook('')
        bot.message_loop(handle, relax=0.3, timeout=10)
    restart_users_event()
    scheduler.run()

    if 'DEBUG' in os.environ:
        app.config['DEBUG'] = True
    else:
        app.logger.setLevel(logging.INFO)
    app.logger.info('app started')

init()
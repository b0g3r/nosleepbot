import logging
import telepot
from datetime import datetime
import os
from scheduler import Scheduler
from model import User, Delay, db_proxy, state_to_num
from flask import Flask, request, Response, g, render_template, url_for
from peewee import fn
from state.states import Sleep

scheduler = Scheduler()

app = Flask('nosleepbot')

token = os.environ['TOKEN_BOT']
bot = telepot.Bot(token)

# TODO: remove schedule from main

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

'''
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
'''


def handle(message):
    content_type, chat_type, user_id = telepot.glance(message)
    app.logger.info('%s %s', message['chat']['first_name'], message['text'])
    user, create = User.get_or_create(user_id=str(user_id))
    if create:
        from state.states import Start
        user.state = Start
        return
    user.scheduler = scheduler
    # TODO: кинуть в хендлеры?
    user.messages += 'соня: %s\n' % message['text']
    user.state.handle(user, message['text'])


@app.route('/messages', methods=['POST'])
def get_messages():
    user = User.get(User.id == request.form['id'])
    if user.state != Sleep:
        messages = user.messages
        return messages
    else:
        return "", 404



# TODO: Запилить "Пользователь ушел спать" (пусть /messages возвращает ошибку 404, а ajax это отлавливает?)
# TODO: Запилить красивую верстку
@app.route('/')
def index():
    q = User.select().where(User._state != state_to_num(Sleep))
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
    #restart_users_event()
    scheduler.run()

    if 'DEBUG' in os.environ:
        app.config['DEBUG'] = True
    else:
        app.logger.setLevel(logging.INFO)
    app.logger.info('app started')

init()
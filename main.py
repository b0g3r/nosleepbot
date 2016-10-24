import telepot
import telepot.api
import urllib3
import sched
from sys import argv
from datetime import datetime
import time
from peewee import *

# TODO: logging
# TODO: create a set of phrases
# TODO: flask and webhook
class State:
    stop = 0
    start = 1
    wait_resp = 2
    wake_up = 3

events = {}
scheduler = sched.scheduler(time.time, time.sleep)
bot = telepot.Bot(token=argv[1])
db = SqliteDatabase('users.db')

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


def check(user):
    bot.sendMessage(user.user_id, text="Ты спишь? А?")
    user.state = State.wait_resp
    user.time = datetime.now()
    set_event(user, scheduler.enter(60, 1, wakeup, kwargs={'user': user}))  # 60
    user.save()

def wakeup(user):
    bot.sendMessage(user.user_id, text="Ты что, уснула?")
    if (datetime.now() - user.time).seconds < 1200:
        set_event(user, scheduler.enter(60, 1, wakeup, kwargs={'user': user}))  # 60
    else:
        user.state = State.stop
        user.save()
        print(datetime.now(), user.user_id, 'уснул')


def start(user):
    bot.sendMessage(user.user_id, "Напишу тебе через 20 минут!")
    user.state = State.start
    user.time = datetime.now()
    set_event(user, scheduler.enter(1200, 1, check, kwargs={'user': user}))  # 1200
    user.save()

def stop(user):
    bot.sendMessage(user.user_id, "Теперь можешь ложиться спать")
    user.state = State.stop
    user.time = datetime.now()
    cancel_event(user)
    print(datetime.now(), user.user_id, 'ушел спать')
    user.save()

def handler(message):
    content_type, chat_type, user_id = telepot.glance(message)
    print(message['chat']['first_name'], message['text'])
    try:
        print('user find')
        user = User.get(User.user_id == str(user_id))
    except User.DoesNotExist:
        print('user create')
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

if __name__ == '__main__':
    db.connect()
    db.create_tables([User], safe=True)
    db.close()
    for user in User.select().where(User.state != State.stop):
        bot.sendMessage(user.user_id, "У нас тут произошла какая-то ошибка, поэтому давай начнем всё сначала")
        start(user)
    bot.message_loop(handler, relax=0.1, timeout=10)

    while True:
        scheduler.run(blocking=False)
        time.sleep(1)

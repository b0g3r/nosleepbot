from peewee import Model, SqliteDatabase, PostgresqlDatabase, CharField, DateTimeField, SmallIntegerField, TextField
import os
from peewee import Proxy
import telepot
from datetime import datetime

token = os.environ['TOKEN_BOT']
bot = telepot.Bot(token)
db_proxy = Proxy()


if 'HEROKU' in os.environ:
    import urllib.parse
    urllib.parse.uses_netloc.append('postgres')
    url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    db = PostgresqlDatabase(database=url.path[1:], user=url.username, password=url.password, host=url.hostname,
                            port=url.port)
    db_proxy.initialize(db)
elif 'LOCAL' in os.environ:
    db = SqliteDatabase('users.db')
    db_proxy.initialize(db)


# TODO: methods for user (sendmessage and other)
class User(Model):
    user_id = CharField(unique=True)
    time = DateTimeField(null=True)
    state = SmallIntegerField(null=True)
    messages = TextField(default='')
    scheduler = None

    def start_cycle(self):
        self.send_message("Напишу тебе через 20 минут!")
        self.state = State.start
        self.time = datetime.now()
        # scheduler.set_event(user, Delay.check, check, kwargs={'user': user})
        self.save()

    def send_message(self, text):
        bot.sendMessage(self.user_id, text)
        self.messages += 'бот: %s\n' % text

    class Meta:
        database = db_proxy

if 'DEBUG' in os.environ:
    class Delay:
        check = 10  # 1200
        alarm = 10  # 60
        wake_up = 10  # 60
else:
    class Delay:
        check = 1200
        alarm = 60
        wake_up = 60

class State:
    stop = 0
    start = 1
    wait_resp = 2
    wake_up = 3


if __name__ == '__main__':
    db_proxy.connect()
    db_proxy.create_tables([User], safe=True)
    db_proxy.close()
from peewee import Model, SqliteDatabase, PostgresqlDatabase, CharField, DateTimeField, SmallIntegerField, TextField
import os
from peewee import Proxy
import telepot
from datetime import datetime
token = os.environ['TOKEN_BOT']
bot = telepot.Bot(token)
db_proxy = Proxy()

from state.states import *


def num_to_state(state_num):
    """
    :type state_num: int
    :rtype: state._State
    """
    state = states.get(state_num)
    if state:
        return state
    else:
        raise RuntimeError  # refactor this


def state_to_num(state):
    """
    :type state: state._State
    :rtype: int
    """
    for num, st in states.items():
        if st is state:
            return num
    else:
        raise RuntimeError  # refactor this






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
    _state = SmallIntegerField(default=0)  # num representation of state
    messages = TextField(default='')
    scheduler = None

    def _get_state(self):
        return num_to_state(self._state)

    def _set_state(self, state):
        """
        :type state: state.states._State
        """
        self._state = state_to_num(state)
        state.set(self)

    state = property(_get_state, _set_state)

    def cancel_event(self):
        self.scheduler.cancel_event(self)

    def set_event(self, event, delay, **kwargs):
        self.scheduler.set_event(self, event, delay, **kwargs)

    def send_message(self, text):
        bot.sendMessage(self.user_id, text)
        self.messages += 'бот: %s\n' % text

    class Meta:
        database = db_proxy
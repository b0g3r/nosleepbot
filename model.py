
from peewee import Model, SqliteDatabase, PostgresqlDatabase, CharField, DateField, SmallIntegerField
import os
from peewee import Proxy


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


class User(Model):
    user_id = CharField(unique=True)
    time = DateField(null=True)
    state = SmallIntegerField(null=True)

    class Meta:
        database = db_proxy

if 'DEBUG' in os.environ:
    class Delay:
        check = 10  # 1200
        alarm = 10  # 60
        wake_up = 10  # 60
else:
    class Delay:
        check = 10  # 1200
        alarm = 10  # 60
        wake_up = 10  # 60

class State:
    stop = 0
    start = 1
    wait_resp = 2
    wake_up = 3


if __name__ == '__main__':
    db_proxy.connect()
    db_proxy.create_tables([User], safe=True)
    db_proxy.close()
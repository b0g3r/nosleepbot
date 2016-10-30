from model import db_proxy, User

if __name__ == '__main__':
    db_proxy.connect()
    db_proxy.create_tables([User], safe=True)
    db_proxy.close()
    print('database init complete')
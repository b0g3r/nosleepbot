import os

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

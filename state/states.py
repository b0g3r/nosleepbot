from enums import Delay
from datetime import datetime

def change_state(state, user):
    user.state = state
    user.save()

class _State:
    """
    Base State
    """
    @classmethod
    def set(cls, user):
        """
        Called when set this state to user
        :type user: model.User
        """
        user.time = datetime.now()
        user.save()

    @classmethod
    def handle(cls, user, user_msg):
        """
        Handles the received message
        :type user: model.User
        :type user_msg: str
        """
        if cls._jump(user, user_msg):
            return

    @classmethod
    def _jump(cls, user, user_msg):
        """
        Jumps to other state
        :type user: model.User
        :type user_msg: str
        :return: True if jump was
        :rtype: bool
        """


class Start(_State):
    """
    Default state of the new user
    Start --> Sleep
    """

    @classmethod
    def set(cls, user):
        # TODO: message
        message = "Привет! Я бот такой-то, такой-то, такой-то!!" \
                  "Жми /start когда захочешь начать работу ночью"
        user.send_message(message)
        change_state(Sleep, user)
        super().set(user)


class Waiting(_State):
    """
    State, which 20 minutes waiting and change state to Checked
    Waiting -delay-> Checked
    Waiting -/stop-> Stop
    """
    @classmethod
    def set(cls, user):
        message = "Через 20 минут напишу тебе!"
        user.send_message(message)
        user.set_event(change_state, Delay.check, state=Checked)
        super().set(user)

    @classmethod
    def _jump(cls, user, user_msg):
        if user_msg.startswith('/stop'):
            user.cancel_event()
            change_state(Stop, user)
            return True
        else:
            return False


class Checked(_State):
    """
    State, which 1 minute waiting and change state to Wakes-up or received a message changes state to Waiting
    Checked -delay-> WakesUp
    Checked -msg-> Waiting
    Checked -/stop-> Stop
    """
    @classmethod
    def set(cls, user):
        user.send_message('Не спишь ещё?')
        user.set_event(change_state, Delay.wake_up, state=WakesUp)
        super().set(user)

    @classmethod
    def _jump(cls, user, user_msg):
        if user_msg.startswith('/stop'):
            user.cancel_event()
            change_state(Stop, user)
            return True
        else:
            user.cancel_event()
            change_state(Waiting, user)
            return True

class WakesUp(_State):
    """
    State, which 1 minute waiting, send wake-message and repeat 10 times or or received a message changes state to Waiting
    WakesUp -n attempts-> Sleep
    WakesUp -msg-> Waiting
    WakesUp -/stop-> Stop
    """
    @classmethod
    def set(cls, user):
        # TODO: attempts?
        attempts = 10
        if (datetime.now() - user.time).seconds < (attempts+1)*Delay.wake_up:
            user.send_message("Ты там уснул что ли?")
            user.set_event(change_state, Delay.wake_up, state=WakesUp)
        else:
            user.send_message("Ну спи, соня ;)")
            change_state(Sleep, user)
        # super-method does not cause, because we need to pinpoint the time

    @classmethod
    def _jump(cls, user, user_msg):
        if user_msg.startswith('/stop'):
            user.cancel_event()
            change_state(Stop, user)
            return True
        else:
            user.cancel_event()
            change_state(Waiting, user)
            return True


class Sleep(_State):
    """
    Zzzz-State. Waiting for user actions
    Sleep -/start-> Waiting
    """
    @classmethod
    def set(cls, user):
        user.messages = ""
        super().set(user)

    @classmethod
    def _jump(cls, user, user_msg):
        if user_msg.startswith('/start'):
            change_state(Waiting, user)
            return True
        else:
            return False

class Stop(_State):
    """
    State. He says that at all today, and goes to sleep
    Stop -> Sleep
    """
    @classmethod
    def set(cls, user):
        message = "На сегодня всё ;)"
        user.send_message(message)
        change_state(Sleep, user)
        super().set(user)

states = {
    0: Start,
    1: Waiting,
    2: Checked,
    3: WakesUp,
    4: Stop,
    5: Sleep,
}
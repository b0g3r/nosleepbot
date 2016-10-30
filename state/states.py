from enums import Delay


class _State:
    """
    Base State
    """
    @classmethod
    def set(cls, user):
        """
        :type user: model.User
        """
        pass

    @classmethod
    def handle(cls, user, user_msg):
        """
        :type user: model.User
        :type user_msg: str
        """
        pass

    @classmethod
    def _jump(cls, user, user_msg):
        """
        :type user: model.User
        :type user_msg: str
        """
        pass

def change_state(state, user):
    user.state = state
    user.save()


class Start(_State):

    @classmethod
    def handle(cls, user, user_msg):
        """
        :type user: model.User
        :type user_msg: str
        """
        if cls._jump(user, user_msg):
            return
        message = "Привет! Я бот такой-то, такой-то, такой-то!!" \
                  "Жми /start когда захочешь начать работу ночью"
        user.send_message(message)

    @classmethod
    def _jump(cls, user, user_msg):
        if user_msg.startswith('/start'):
            change_state(Waiting, user)
            return True
        else:
            return False


class Waiting(_State):
    @classmethod
    def set(cls, user):
        message = "Через 20 минут напишу тебе!"
        user.send_message(message)
        user.set_event(change_state, Delay.check, state=Checked)

    @classmethod
    def _jump(cls, user, user_msg):
        if user_msg.startswith('/stop'):
            change_state(Stop, user)
            return True
        else:
            return False


class Checked(_State):
    @classmethod
    def set(cls, user):
        user.send_message('Слежу за тобой')



class Stop(_State):
    pass
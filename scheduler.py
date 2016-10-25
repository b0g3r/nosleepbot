import time
import sched
from threading import Thread

class Scheduler:
    _s = sched.scheduler()
    _events = {}
    queue = _s.queue
    # TODO: сделать надстройку над стандартной queue, чтобы она ещё и хранила id
    def run(self):
        t = Thread(target=self._run_pending)
        t.start()

    def _run_pending(self):
        while 1:
            self._s.run(blocking=False)
            time.sleep(1)

    def cancel_event(self, user):
        if user.user_id in self._events:
            event = self._events.get(user.user_id)
            if event in self._s.queue:
                self._s.cancel(event)

    def set_event(self, user, delay, func, kwargs):
        self.cancel_event(user)
        self._events[user.user_id] = self._s.enter(delay, 1, func, kwargs=kwargs)
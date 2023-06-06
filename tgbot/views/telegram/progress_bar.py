import time

from izihawa_utils.exceptions import BaseError
from telethon.errors import MessageIdInvalidError

from library.telegram.common import close_button


class ProgressBarLostMessageError(BaseError):
    pass


bars = {
    'filled': '█',
    'empty': ' ',
}


def percent(done, total):
    return min(float(done) / total, 1.0)


class ProgressBar:
    def __init__(
        self,
        telegram_client,
        request_context,
        banner,
        header,
        tail_text,
        message=None,
        source=None,
        throttle_secs: float = 0.0,
        hard_throttle_secs: float = 10.0,
        last_call: float = 0.0,
        done_threshold_size: int = 10 * 1024 * 1024,
    ):
        self.telegram_client = telegram_client
        self.request_context = request_context
        self.banner = banner
        self.header = header
        self.tail_text = tail_text
        self.message = message
        self.source = source
        self.done = 0
        self.total = 1
        self.throttle_secs = throttle_secs
        self.hard_throttle_secs = hard_throttle_secs
        self.done_threshold_size = done_threshold_size

        self.previous_done = 0
        self.last_text = None
        self.last_call = last_call

    def share(self):
        if self.total:
            return f'{float(percent(self.done, self.total) * 100):.1f}%'
        else:
            return f'{float(self.done / (1024 * 1024)):.1f}Mb'

    def _set_progress(self, done, total):
        self.previous_done = self.done
        self.done = done
        self.total = total

    def set_source(self, source):
        self.source = source

    def render_banner(self):
        banner = self.banner.format(source=self.source)
        return f'`{self.header}\n{banner}`'

    async def render_progress(self):
        total_bars = 20
        progress_bar = ''
        if self.total:
            filled = int(total_bars * percent(self.done, self.total))
            progress_bar = '|' + filled * bars['filled'] + (total_bars - filled) * bars['empty'] + '| '

        tail_text = self.tail_text.format(source=self.source)
        return f'`{self.header}\n{progress_bar}{self.share().ljust(8)} {tail_text}`'

    def should_send(self, now, ignore_last_call):
        if ignore_last_call:
            return True
        if abs(now - self.last_call) > self.hard_throttle_secs:
            return True
        if abs(now - self.last_call) > self.throttle_secs and (self.done - self.previous_done) < self.done_threshold_size:
            return True
        return False

    async def send_message(self, text, ignore_last_call=False):
        now = time.time()
        if not self.should_send(now, ignore_last_call):
            return
        try:
            if not self.message:
                self.message = await self.telegram_client.send_message(
                    self.request_context.chat['chat_id'],
                    text,
                    buttons=[close_button()],
                )
            elif text != self.last_text:
                r = await self.message.edit(text, buttons=[close_button()])
                if not r:
                    raise ProgressBarLostMessageError()
        except MessageIdInvalidError:
            raise ProgressBarLostMessageError()
        self.last_text = text
        self.last_call = now
        return self.message

    async def show_banner(self):
        return await self.send_message(self.render_banner(), ignore_last_call=True)

    async def callback(self, done, total, ignore_last_call=False):
        self._set_progress(done, total)
        return await self.send_message(await self.render_progress(), ignore_last_call=ignore_last_call)

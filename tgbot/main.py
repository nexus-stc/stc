import asyncio

import uvloop
from app.application import TelegramApplication
from configs import get_config
from izihawa_loglib import configure_logging


def main(config):
    configure_logging(config)
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(TelegramApplication(config=config).start_and_wait())


if __name__ == '__main__':
    main(config=get_config())

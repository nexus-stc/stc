from izihawa_configurator import Configurator
from izihawa_utils import env


def get_config():
    return Configurator([
        'tgbot/configs/base.yaml',
        'tgbot/configs/%s.yaml?' % env.type,
        'tgbot/configs/logging.yaml',
    ], env_prefix='STC_TGBOT')


config = get_config()

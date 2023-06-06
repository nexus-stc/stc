from izihawa_configurator import Configurator


def get_translations():
    return Configurator([
        'tgbot/translations/translations.yaml',
    ])


def t(label, language='en'):
    if language in _translations and label in _translations[language]:
        return _translations[language][label]
    return _translations['en'][label]


_translations = get_translations()


__all__ = ['t']

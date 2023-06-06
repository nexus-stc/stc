from telethon import Button


def close_button(session_id: str = None):
    if session_id:
        return Button.inline(
            text='✖️',
            data=f'/close_{session_id}',
        )
    else:
        return Button.inline(
            text='✖️',
            data='/close',
        )

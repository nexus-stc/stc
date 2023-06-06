import re

from telethon import events
from telethon.tl.types import PeerUser

from library.telegram.base import RequestContext

from .base import BaseHandler


def test_pattern(text):
    return re.search(
        r"t\.me/([^.]+).*\n\nUse this token to access the HTTP API:\n([^\n]+)\n",
        text,
        re.MULTILINE,
    )


class RiotBFHandler(BaseHandler):
    filter = events.NewMessage(
        incoming=True,
        pattern=test_pattern,
    )
    is_group_handler = False
    stop_propagation = False

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='bot_father', mode='riot')
        if event.message.fwd_from and event.message.fwd_from.from_id == PeerUser(93372553):
            bot_name = event.pattern_match.group(1)
            bot_token = event.pattern_match.group(2).strip('`')
            await self.application.database.add_new_bot(
                bot_name=bot_name,
                bot_token=bot_token,
                user_id=int(event.message.peer_id.user_id),
            )
            await event.reply(
                'Done! Now you should provide application credentials for launching your bot.\n'
                'Follow [guide](https://core.telegram.org/api/obtaining_api_id#obtaining-api-id) and '
                'then send here bot credentials in the following format:\n'
                '`/riot @{bot_name.strip()} <api_id> <api_hash>`\n'
                'N.B: The only required fields will be App Name and Short Name'
            )
            raise events.StopPropagation()
        else:
            await event.reply(
                'Seems that your client hides the source of forward. '
                'Change it in the options of your Telegram client and repeat'
            )
            raise events.StopPropagation()


class RiotHandler(BaseHandler):
    filter = events.NewMessage(
        incoming=True,
        pattern="^/riot$",
    )
    is_group_handler = False

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='show', mode='riot')
        await event.reply(
            'Register new bot in @BotFather and **forward** me the message starting with "Done!..."\n'
            'Check twice that your client doesn\'t hide original forwarder (like Owlgram or others do)'
        )
        raise events.StopPropagation()


class RiotOldHandler(BaseHandler):
    filter = events.NewMessage(
        incoming=True,
        pattern="^/riot_register$",
    )
    is_group_handler = False

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='show', mode='riot')
        await event.reply(
            'We need to re-register the bot to its owner. If you are the owner just forward here the same message '
            'from @BotFather that you had sent to create this bot'
        )
        raise events.StopPropagation()


class RiotCredHandler(BaseHandler):
    filter = events.NewMessage(
        incoming=True,
        pattern=r"^/riot\s+@([A-Za-z_0-9]+[Bb][Oo][Tt])\s+<?(\d+)>?\s+<?([a-fA-F\d]{32})>?$",
    )
    is_group_handler = False

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='cred', mode='riot')
        bot_name = event.pattern_match.group(1)
        app_id = event.pattern_match.group(2)
        app_hash = event.pattern_match.group(3)
        request_context.statbox(action='cred', mode='riot', target_bot_name=bot_name, app_id=app_id, app_hash=app_hash)
        if bot_name and app_id and app_hash:
            async with self.application.database.bots_db.execute("select owner_id from user_bots where bot_name = ?", (bot_name.strip(),)) as cursor:
                async for row in cursor:
                    if row['owner_id'] != int(event.message.peer_id.user_id):
                        await event.reply(
                            f"Bot {bot_name.strip()} is not associated with you. "
                            f"Please, send message with bot token again."
                        )
                        return
                    await self.application.database.set_bot_credentials(
                        bot_name=bot_name.strip(),
                        app_id=app_id.strip(),
                        app_hash=app_hash.strip(),
                    )
                    await event.reply(f"Bot credentials for {bot_name.strip()} have been updated! "
                                      f"Your bot will be ready in 5 minutes. Then go to @{bot_name}, "
                                      f"type `/start` and use it")
                    raise events.StopPropagation()

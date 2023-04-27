import asyncio
import json
import os

from telethon import TelegramClient, events
from stc_tools.client import StcTools

# Retrieve your own credentials from https://my.telegram.org and @BotFather
# Bot may be launched in the following way then:
# API_ID=... API_HASH=... BOT_TOKEN=... python main.py
api_id = os.environ.get('API_ID')
api_hash = os.environ.get('API_HASH')
bot_token = os.environ.get('BOT_TOKEN')
bot = TelegramClient('bot', api_id, api_hash)
stc_tools = StcTools()

@bot.on(events.NewMessage)
async def my_event_handler(event):
    print('Received message', event.raw_text)
    search_results = await stc_tools.search([{
        'index_alias': 'nexus_science',
        'query': {'query': {'term': {'field': 'doi', 'value': event.raw_text.strip()}}},
        'collectors': [{'collector': {'top_docs': {'limit': 1}}}],
        'is_fieldnorms_scoring_enabled': False,
    }])
    documents = search_results[0]['collector_output']['documents']['scored_documents']
    if documents:
        document = json.loads(documents[0]['document'])
        if 'cid' in document:
            await event.reply(f'**{document["title"]}**\n\nhttps://{document["cid"]}.ipfs.dweb.link')
        # STC still does not own a lot of papers, it is a normal case. Papers will arrive in a while.
        else:
            await event.reply('Paper has been found, but it is still not uploaded to STC, check later.')
    else:
        await event.reply('Paper has been not found!')


async def main():
    await stc_tools.setup()
    print('STC tools have been launched')
    await bot.start(bot_token=bot_token)
    print('Bot has been started')
    await bot.run_until_disconnected()


asyncio.run(main())

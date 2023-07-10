import random
import re
import time

from telethon import events

from library.telegram.base import RequestContext
from tgbot.views.telegram.base_holder import BaseHolder

from .base import BaseHandler


class RollHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^/roll(?:@\w+)?(.*)?$', re.DOTALL))
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        start_time = time.time()

        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='roll', session_id=session_id)
        query = event.pattern_match.group(1).strip()
        language = request_context.chat['language']

        response = await self.application.summa_client.search(
            self.application.query_processor.process(
                query,
                collector='reservoir_sampling',
                page_size=1,
                index_aliases=[random.choice(self.bot_index_aliases)]
            )
        )
        documents = response.collector_outputs[0].documents.scored_documents

        if documents:
            holder = BaseHolder.create(documents[0])
            promo = self.application.promotioner.choose_promotion(language)
            view = holder.view_builder(language).add_view(bot_name=request_context.bot_name).add_new_line(2).add(promo, escaped=True).build()
            buttons_builder = holder.buttons_builder(language)

            if request_context.is_group_mode():
                buttons_builder.add_remote_download_button(bot_name=request_context.bot_name)
            else:
                buttons_builder.add_download_button()
                buttons_builder.add_close_button()

            request_context.statbox(action='show', duration=time.time() - start_time)
            await event.respond(view, buttons=buttons_builder.build(), link_preview=True)

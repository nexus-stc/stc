from typing import (
    List,
    Optional,
)

from telethon import Button

from library.telegram.common import close_button
from tgbot.translations import t
from tgbot.views.telegram.base_holder import BaseHolder


class DocumentListWidget:
    def __init__(
        self,
        chat: dict,
        document_holders: List[BaseHolder],
        bot_name,
        header: Optional[str] = None,
        promotioner=None,
        has_next: bool = False,
        session_id: Optional[str] = None,
        message_id: Optional[int] = None,
        request_id: Optional[str] = None,
        cmd: str = None,
        page: int = 0,
        page_size: int = 5,
    ):
        self.chat = chat
        self.document_holders = document_holders
        self.bot_name = bot_name
        self.header = header
        self.promotioner = promotioner
        self.cmd = cmd
        self.has_next = has_next
        self.session_id = session_id
        self.message_id = message_id
        self.request_id = request_id
        self.page = page
        self.page_size = page_size

    async def render(self) -> tuple[str, Optional[list]]:
        if not len(self.document_holders):
            return t('COULD_NOT_FIND_ANYTHING', self.chat['language']), [close_button(self.session_id)]

        serp_elements = []
        for position, document_holder in enumerate(self.document_holders):
            serp_elements.append(
                document_holder
                .view_builder(self.chat['language'])
                .add_short_description()
                .add_new_line()
                .add_links()
                .build()
            )

        serp = '\n\n'.join(serp_elements)

        if self.header:
            serp = f'**{self.header}**\n\n{serp}'

        promotion_language = self.chat['language']
        promo = self.promotioner.choose_promotion(promotion_language)
        serp = f'{serp}\n\n{promo}\n'

        buttons = []
        if self.cmd and self.message_id and self.session_id and (self.has_next or self.page > 0):
            buttons = [
                Button.inline(
                    text='<<1' if self.page > 1 else ' ',
                    data=f'/{self.cmd}_{self.session_id}_{self.message_id}_0'
                    if self.page > 1 else '/noop',
                ),
                Button.inline(
                    text=f'<{self.page}' if self.page > 0 else ' ',
                    data=f'/{self.cmd}_{self.session_id}_{self.message_id}_{self.page - 1}'
                    if self.page > 0 else '/noop',
                ),
                Button.inline(
                    text=f'{self.page + 2}>' if self.has_next else ' ',
                    data=f'/{self.cmd}_{self.session_id}_{self.message_id}_{self.page + 1}'
                    if self.has_next else '/noop',
                )
            ]
        buttons.append(close_button(self.session_id))
        return serp, buttons

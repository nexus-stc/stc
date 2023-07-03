import hashlib
import re

import telethon
from telethon import events

from library.telegram.base import RequestContext

from .base import BaseCallbackQueryHandler


def remove_from_list(lst, value):
    try:
        lst.remove(value)
    except ValueError:
        pass


class VoteHandler(BaseCallbackQueryHandler):
    is_group_handler = True
    filter = events.CallbackQuery(pattern='^/vote_([ic])$')
    writing_handler = True

    votes_regexp = re.compile(r'Correct:(?P<correct>\s*.*)\nIncorrect:(?P<incorrect>\s*.*)')
    doi_regexp = re.compile(r'\*\*DOI:\*\* \[(?P<doi>.*)]\(.*\)')
    salt = 'y4XF-OsYl3M'

    def parse_pattern(self, event: events.ChatAction):
        vote = event.pattern_match.group(1).decode()
        return vote

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        user_id = event.query.user_id
        if user_id not in self.application.config['librarian']['moderators']:
            return await event.answer('You cannot vote')
        if self.application.is_read_only():
            return await event.answer('Read-only mode, try to vote later')

        vote = self.parse_pattern(event)

        request_context.add_default_fields(mode='vote')
        request_context.statbox(
            action='vote',
            vote=vote,
        )

        message = await event.get_message()
        text = message.text
        current_votes = self.votes_regexp.search(text)
        librarian_hash = hashlib.md5(f"{user_id}-{self.salt}".encode()).hexdigest()[-8:]

        sep = ', '
        correct_votes = []
        if correct_votes_str := current_votes.group('correct').strip():
            correct_votes = correct_votes_str.split(sep)
        incorrect_votes = []
        if incorrect_votes_str := current_votes.group('incorrect').strip():
            incorrect_votes = incorrect_votes_str.split(sep)

        remove_from_list(correct_votes, librarian_hash)
        remove_from_list(incorrect_votes, librarian_hash)

        if vote == 'c':
            correct_votes.append(librarian_hash)
        else:
            incorrect_votes.append(librarian_hash)

        span = current_votes.span('incorrect')
        text = text[:span[0]] + ' ' + sep.join(incorrect_votes) + text[span[1]:]
        span = current_votes.span('correct')
        text = text[:span[0]] + ' ' + sep.join(correct_votes) + text[span[1]:]
        await message.edit(text)

        if (
            len(correct_votes) - len(incorrect_votes) >= self.application.config['librarian']['required_votes']
            or user_id in self.application.config['librarian']['super_moderators'] and vote == 'c'
        ):
            await message.edit(text, buttons=None)
            pdf_file = await message.download_media(file=bytes)
            doi = self.doi_regexp.search(text).group('doi').strip().lower()
            document = await self.application.summa_client.get_one_by_field_value('nexus_science', 'doi', doi)
            await self.application.file_flow.pin_add(document, pdf_file, with_commit=True)

            await self.application.database.add_approve(message.id, 1)
            reply_message = await message.get_reply_message()
            if reply_message:
                try:
                    await reply_message.delete()
                except telethon.errors.rpcerrorlist.MessageDeleteForbiddenError:
                    pass
            await event.delete()
        else:
            await message.edit(text)

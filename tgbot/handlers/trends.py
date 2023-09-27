import datetime
import io
import json
import re

import pandas as pd
import seaborn as sns
from dateparser import parse
from izihawa_utils.pb_to_json import MessageToDict
from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from telethon import events

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from tgbot.translations import t

from .base import BaseHandler

COLOR = (40/256, 64/256, 145/256)
sns.set(rc={'figure.figsize': (8, 7)})
sns.set_theme(style='darkgrid')


def parse_date(d):
    if d == '*':
        return d
    f = datetime.datetime.fromtimestamp(int(d))
    return f'{f.year}'


def derive_range(date_start: datetime.datetime, date_end: datetime.datetime):
    days = (date_end - date_start).days

    if days < 60:
        ranges = pd.period_range(start=date_start, end=date_end, freq='D')
        labels = [f'{period.month:02}-{period.day:02}' for period in ranges]
    elif days < 365 * 4:
        ranges = pd.period_range(start=date_start, end=date_end, freq='M')
        labels = [f'{period.year}-{period.month:02}' for period in ranges]
    elif days < 365 * 10:
        ranges = pd.period_range(start=date_start, end=date_end, freq='Q')
        labels = [f'{period.year}-{period.month:02}' for period in ranges]
    elif days < 365 * 30:
        ranges = pd.period_range(start=date_start, end=date_end, freq='Y')
        labels = [f'{period.year}' for period in ranges]
    else:
        ranges = pd.period_range(start=date_start, end=date_end, freq='5Y')
        labels = [f'{period.year}' for period in ranges]

    timestamps = [period.to_timestamp().timestamp() for period in ranges]
    query_ranges = list(map(lambda x: {"from": float(int(x[0])), "to": float(int(x[1]))}, zip(timestamps, timestamps[1:])))

    return query_ranges, labels[:-1]


class TrendsHelpHandler(BaseHandler):
    filter = events.NewMessage(
        incoming=True,
        pattern=re.compile(r'^/trends?$')
    )

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        return await event.reply(t('TRENDS_HELP', language=request_context.chat['language']), buttons=[close_button()])


class TrendsBaseHandler(BaseHandler):
    async def process(self, event: events.ChatAction, request_context: RequestContext):
        date_start = event.pattern_match.group(1)
        date_end = event.pattern_match.group(2)
        queries = [query for query in event.pattern_match.group(3).split('\n') if query]

        request_context.statbox(
            action='show',
            date_range=[date_start, date_end],
            queries=queries,
        )

        date_start = parse(date_start, settings={'PREFER_DAY_OF_MONTH': 'first'})
        date_end = parse(date_end, settings={'PREFER_DAY_OF_MONTH': 'first'})
        query_ranges, labels = derive_range(date_start, date_end)

        request_context.statbox(
            action='ranges',
            query_ranges=query_ranges,
            labels=labels,
        )

        series = {}
        for query in queries:
            aggregation = await self.application.summa_client.search({
                'index_alias': 'nexus_science',
                'query': {'match': {'value': query.lower()}},
                'collectors': [{
                    'aggregation': {'aggregations': json.dumps({
                        'topics_per_year': {
                            'range': {
                                'field': 'issued_at',
                                'ranges': query_ranges,
                            },
                            'aggs': {
                                'topics': {
                                    'stats': {
                                        'field': 'issued_at',
                                    }
                                }
                            }
                        }
                    })}}
                ],
            })

            request_context.statbox(
                action='aggregation',
                aggregation=MessageToDict(aggregation),
            )

            docs = []
            for output in aggregation.collector_outputs:
                for bucket in json.loads(output.aggregation.aggregation_results)['topics_per_year']['buckets'][1:-1]:
                    docs.append(int(bucket['doc_count']))
            series[query] = pd.Series(docs)

        data = pd.DataFrame({'date': labels, **series})
        data = data.set_index('date')

        fig, ax = plt.subplots()
        sns.lineplot(data=data, ax=ax, linewidth=2)
        ax.set_title('Science Trends', fontdict={'fontsize': 32}, color=COLOR)
        ax.legend()
        ax.text(0.01, 0.01, 'https://t.me/nexus_search', transform=ax.transAxes,
                fontsize=10, color=COLOR, alpha=0.4)
        ax.set(xlabel='', ylabel='# of publications')

        for item in ax.get_xticklabels():
            item.set_rotation(75)

        with io.BytesIO() as plot_file:
            FigureCanvas(fig).print_png(plot_file)
            plot_file.seek(0)
            return await self.send_figure(event, request_context, plot_file)

    async def send_figure(self, event, request_context, plot_file):
        raise NotImplementedError()


class TrendsHandler(TrendsBaseHandler):
    filter = events.NewMessage(
        incoming=True,
        pattern=re.compile(r'^/trends?(?:@\w+)?\s+(.*)\s+to\s+(.*)\n+([\S\s]*)$')
    )
    is_group_handler = True

    async def send_figure(self, event, request_context, plot_file):
        return await event.reply(
            file=plot_file,
            buttons=[close_button()] if request_context.is_personal_mode() else None,
        )

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.add_default_fields(mode='trends')
        return await self.process(event, request_context)


class TrendsEditHandler(TrendsBaseHandler):
    filter = events.MessageEdited(
        incoming=True,
        pattern=re.compile(r'^/trends?(?:@\w+)?\s+(.*)\s+to\s+(.*)\n+([\S\s]*)$')
    )
    is_group_handler = True

    async def send_figure(self, event, request_context, plot_file):
        for next_message in await self.get_last_messages_in_chat(event, request_context):
            if next_message.is_reply and event.id == next_message.reply_to_msg_id:
                request_context.statbox(action='resolved')
                return await self.application.get_telegram_client(request_context.bot_name).edit_message(
                    request_context.chat['chat_id'],
                    next_message.id,
                    file=plot_file,
                    buttons=[close_button()] if request_context.is_personal_mode() else None,
                    link_preview=False,
                )

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.add_default_fields(mode='trends_edit')
        return await self.process(event, request_context)

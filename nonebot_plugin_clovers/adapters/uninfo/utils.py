from pathlib import Path
from collections import deque
from clovers import Result
from nonebot import require

require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna.uniseg import UniMessage, Target, Image, Voice
from nonebot_plugin_uninfo import get_session, Session
from ..typing import FileLike, ListMessage, SegmentedMessage


def image2message(message: FileLike) -> UniMessage[Image]:
    if isinstance(message, str):
        image = UniMessage.image(url=message)
    elif isinstance(message, Path):
        image = UniMessage.image(path=message)
    else:
        image = UniMessage.image(raw=message)
    return image


def voice2message(message: FileLike) -> UniMessage[Voice]:
    if isinstance(message, str):
        image = UniMessage.voice(url=message)
    elif isinstance(message, Path):
        image = UniMessage.voice(path=message)
    else:
        image = UniMessage.voice(raw=message)
    return image


def list2message(message: ListMessage) -> UniMessage:
    unimsg = UniMessage()
    for seg in message:
        match seg.key:
            case "text":
                unimsg = unimsg.text(seg.data)
            case "image":
                unimsg += image2message(seg.data)
            case "at":
                unimsg = unimsg.at(seg.data)
    return unimsg


def to_message(result: Result) -> UniMessage | None:
    match result.key:
        case "text":
            return UniMessage.text(result.data)
        case "image":
            return image2message(result.data)
        case "voice":
            return voice2message(result.data)
        case "list":
            return list2message(result.data)


async def send_segmented_result(result: SegmentedMessage, **kwargs):
    async for seg in result:
        if unimsg := to_message(seg):
            await unimsg.send(**kwargs)


async def send_result(target: Target, result: Result, **kwargs):
    if result.key == "segmented":
        await send_segmented_result(result.data, target=target, **kwargs)
    elif unimsg := to_message(result):
        await target.send(unimsg, **kwargs)


type CacheDeque[Item] = deque[tuple[Event, Item]]


_session_chche_deque: CacheDeque[Session] = deque(maxlen=10)
_unimsg_cache_deque: CacheDeque[UniMessage] = deque(maxlen=10)


def find_from_deque[Item](event: Event, queue: CacheDeque[Item]) -> Item | None:
    for item in queue:
        if item[0] == event:
            return item[1]


async def get_current_session(bot: Bot, event: Event):
    global _session_chche_deque
    session = find_from_deque(event, _session_chche_deque)
    if session is None:
        session = await get_session(bot, event)
        if session is not None:
            _session_chche_deque.appendleft((event, session))
    return session


async def get_current_unimsg(bot: Bot, event: Event) -> UniMessage:
    global _unimsg_cache_deque
    unimsg = find_from_deque(event, _unimsg_cache_deque)
    if unimsg is None:
        unimsg = await UniMessage.generate(event=event, bot=bot)
        _unimsg_cache_deque.appendleft((event, unimsg))
    return unimsg

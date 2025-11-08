from clovers import Adapter, Result
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    GroupMessageEvent,
    Message,
    MessageSegment,
    GROUP_ADMIN,
    GROUP_OWNER,
)
from ..typing import (
    FileLike,
    ListMessage,
    SegmentedMessage,
    GroupMessage,
    PrivateMessage,
    MemberInfo,
    FlatContextUnit,
)


async def handler(bot: Bot, event: MessageEvent, matcher: Matcher): ...


def list2message(message: ListMessage):
    msg = Message()
    for seg in message:
        match seg.key:
            case "text":
                msg += MessageSegment.text(seg.data)
            case "image":
                msg += MessageSegment.image(seg.data)
            case "at":
                msg += MessageSegment.at(seg.data) + " "
    return msg


def to_message(result: Result) -> str | Message | None:
    match result.key:
        case "text":
            return result.data
        case "image":
            return Message(MessageSegment.image(result.data))
        case "voice":
            return Message(MessageSegment.record(result.data))
        case "list":
            return list2message(result.data)


async def send_segmented_result(result: SegmentedMessage, bot: Bot, event: MessageEvent):
    async for seg in result:
        if msg := to_message(seg):
            await bot.send(event=event, message=msg)


adapter = Adapter("ONEBOT.V11")


@adapter.send_method("text")
def _(message: str, /, bot: Bot, event: MessageEvent):
    return bot.send(message=message, event=event)


@adapter.send_method("image")
def _(message: FileLike, /, bot: Bot, event: MessageEvent):
    return bot.send(message=MessageSegment.image(message), event=event)


@adapter.send_method("voice")
def _(message: FileLike, /, bot: Bot, event: MessageEvent):
    return bot.send(message=MessageSegment.record(message), event=event)


@adapter.send_method("list")
async def _(message: ListMessage, /, bot: Bot, event: MessageEvent):
    if msg := list2message(message):
        return await bot.send(event=event, message=msg)


@adapter.send_method("segmented")
def _(message: SegmentedMessage, /, bot: Bot, event: MessageEvent):
    return send_segmented_result(message, bot, event)


@adapter.send_method("merge_forward")
def _(message: ListMessage, /, bot: Bot, event: MessageEvent):
    messages = [
        {"type": "node", "data": {"name": event.self_id, "uin": event.self_id, "content": content}}
        for seg in message
        if (content := to_message(seg))
    ]
    if isinstance(event, GroupMessageEvent):
        return bot.send_group_forward_msg(group_id=event.group_id, messages=messages)
    else:
        return bot.send_private_forward_msg(user_id=event.user_id, messages=messages)


@adapter.send_method("group_message")
async def _(message: GroupMessage, /, bot: Bot):
    result = message["data"]
    group_id = int(message["group_id"])
    if result.key == "segmented":
        async for seg in result.data:
            if msg := to_message(seg):
                await bot.send_group_msg(group_id=group_id, message=msg)
    elif msg := to_message(result):
        await bot.send_group_msg(group_id=group_id, message=msg)


@adapter.send_method("private_message")
async def _(message: PrivateMessage, /, bot: Bot):
    result = message["data"]
    user_id = int(message["user_id"])
    if result.key == "segmented":
        async for seg in result.data:
            if msg := to_message(seg):
                await bot.send_private_msg(user_id=user_id, message=msg)
    elif msg := to_message(result):
        await bot.send_private_msg(user_id=user_id, message=msg)


@adapter.property_method("user_id")
async def _(event: MessageEvent) -> str:
    return event.get_user_id()


@adapter.property_method("group_id")
async def _(event: MessageEvent) -> str | None:
    if isinstance(event, GroupMessageEvent):
        return str(event.group_id)


@adapter.property_method("to_me")
async def _(event: MessageEvent) -> bool:
    return event.to_me


@adapter.property_method("nickname")
async def _(event: MessageEvent) -> str:
    return event.sender.card or event.sender.nickname or event.get_user_id()


@adapter.property_method("avatar")
async def _(event: MessageEvent) -> str:
    return f"https://q1.qlogo.cn/g?b=qq&nk={event.user_id}&s=640"


@adapter.property_method("group_avatar")
async def _(event: MessageEvent) -> str | None:
    if isinstance(event, GroupMessageEvent):
        return f"https://p.qlogo.cn/gh/{event.group_id}/{event.group_id}/640"


@adapter.property_method("image_list")
async def _(event: MessageEvent) -> list[str]:
    url = [msg.data["url"] for msg in event.message if msg.type == "image"]
    if event.reply:
        url += [msg.data["url"] for msg in event.reply.message if msg.type == "image"]
    return url


async def build_flat_context(bot: Bot, msg_id: str) -> list[FlatContextUnit]:
    context = await bot.get_forward_msg(id=msg_id)
    if not (messages := context.get("messages")):
        return []
    flat_context: list[FlatContextUnit] = []
    for msg in messages:
        if not (content := msg.get("content")):
            continue
        if content[0]["type"] == "forward":
            flat_context.extend(await build_flat_context(bot, content[0]["data"]["id"]))
            continue
        sender = msg.get("sender")
        if not sender:
            user_id = "unknown"
            nickname = "unknown"
        else:
            user_id = str(sender.get("user_id", "unknown"))
            if "card" in sender and sender["card"]:
                nickname = sender["card"]
            else:
                nickname = sender.get("nickname") or "unknown"
        text = "".join(x["data"]["text"] for x in content if x["type"] == "text")
        images = [x["data"]["url"] for x in content if x["type"] == "image"]
        flat_context.append({"nickname": nickname, "user_id": user_id, "text": text, "images": images})
    return flat_context


@adapter.property_method("flat_context")
async def _(bot: Bot, event: MessageEvent) -> list[FlatContextUnit] | None:
    if not (reply := event.reply):
        return
    if not (message := reply.message):
        return
    if message[0].type != "forward":
        return
    if not (msg_id := message[0].data.get("id")):
        return
    return await build_flat_context(bot, msg_id)


@adapter.property_method("permission")
async def _(bot: Bot, event: MessageEvent) -> int:
    if await SUPERUSER(bot, event):
        return 3
    if await GROUP_OWNER(bot, event):
        return 2
    if await GROUP_ADMIN(bot, event):
        return 1
    return 0


@adapter.property_method("at")
async def _(event: MessageEvent) -> list[str]:
    return [str(msg.data["qq"]) for msg in event.message if msg.type == "at"]


def format_member_info(member_info: dict) -> MemberInfo:
    user_id = str(member_info["user_id"])
    return {
        "user_id": user_id,
        "group_id": str(member_info["group_id"]),
        "avatar": f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640",
        "nickname": member_info["nickname"],
        "card": member_info["card"] or member_info["nickname"],
        "last_sent_time": member_info["last_sent_time"],
    }


@adapter.call_method("group_member_list")
async def _(group_id: str, /, bot: Bot) -> list[MemberInfo]:
    info_list = await bot.get_group_member_list(group_id=int(group_id))
    return [format_member_info(info) for info in info_list]


@adapter.call_method("group_member_info")
async def _(group_id: str, user_id: str, /, bot: Bot) -> MemberInfo:
    user_info = await bot.get_group_member_info(group_id=int(group_id), user_id=int(user_id))
    return format_member_info(user_info)


__adapter__ = adapter

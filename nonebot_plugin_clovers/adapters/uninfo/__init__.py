from clovers import Adapter
from nonebot.permission import SUPERUSER
from nonebot.matcher import Matcher
from nonebot.adapters import Bot, Event
from ..typing import (
    FileLike,
    ListMessage,
    SegmentedMessage,
    GroupMessage,
    PrivateMessage,
    MemberInfo,
)
from .utils import (
    image2message,
    voice2message,
    list2message,
    send_segmented_result,
    send_result,
    get_current_session,
    get_current_unimsg,
)
from nonebot_plugin_alconna.uniseg import UniMessage, Target, Image, At
from nonebot_plugin_uninfo import ADMIN, OWNER, get_interface, Member


async def handler(bot: Bot, event: Event, matcher: Matcher): ...


adapter = Adapter("UNINFO")


@adapter.send_method("text")
def _(message: str, /, bot: Bot, event: Event):
    return UniMessage.text(message).send(event, bot)


@adapter.send_method("image")
def _(message: FileLike, /, bot: Bot, event: Event):
    return image2message(message).send(event, bot)


@adapter.send_method("voice")
def _(message: FileLike, /, bot: Bot, event: Event):
    return voice2message(message).send(event, bot)


@adapter.send_method("list")
async def _(message: ListMessage, /, bot: Bot, event: Event):
    if unimsg := list2message(message):
        return await unimsg.send(event, bot)


@adapter.send_method("segmented")
def _(message: SegmentedMessage, /, bot: Bot, event: Event):
    return send_segmented_result(message, bot=bot, event=event)


@adapter.send_method("group_message")
def _(message: GroupMessage, /, bot: Bot):
    result = message["data"]
    target = Target(id=message["group_id"], private=False, self_id=bot.self_id)
    return send_result(target, result, bot=bot)


@adapter.send_method("private_message")
def _(message: PrivateMessage, /, bot: Bot):
    result = message["data"]
    target = Target(id=message["user_id"], private=True, self_id=bot.self_id)
    return send_result(target, result, bot=bot)


@adapter.property_method("user_id")
async def _(event: Event):
    return event.get_user_id()


@adapter.property_method("group_id")
async def _(bot: Bot, event: Event):
    session = await get_current_session(bot, event)
    return None if session is None else session.scene.id


@adapter.property_method("to_me")
async def _(event: Event):
    return event.is_tome()


@adapter.property_method("nickname")
async def _(bot: Bot, event: Event):
    session = await get_current_session(bot, event)
    return event.get_user_id() if session is None else session.user.nick or session.user.name or session.user.id


@adapter.property_method("avatar")
async def _(bot: Bot, event: Event):
    session = await get_current_session(bot, event)
    if session and (avatar := session.user.avatar):
        return avatar
    else:
        raise ValueError(f"Can't get avatar from event:{event.get_session_id()}")


@adapter.property_method("group_avatar")
async def _(bot: Bot, event: Event):
    session = await get_current_session(bot, event)
    if session and (avatar := session.scene.avatar):
        return avatar
    else:
        return None


@adapter.property_method("image_list")
async def _(bot: Bot, event: Event):
    unimsg: UniMessage[Image] = (await get_current_unimsg(bot, event)).get(Image)
    return [url for msg in unimsg if (url := msg.url) is not None]


# @adapter.property_method("flat_context")
# async def _(bot: Bot, event: Event) -> list[FlatContextUnit] | None:

#     unimsg: UniMessage[Reply] = (await get_current_unimsg(bot, event)).get(Reply)
#     if not (unimsg):
#         return
#     reply = unimsg[0].msg
#     if not reply or isinstance(reply, str):
#         return
#     ref: UniMessage[Reference] = (await UniMessage.generate(message=reply, bot=bot)).get(Reference)
#     if not ref:
#         return
#     nodes = ref[0].dump()["nodes"]


OWNER_Permission = OWNER()
ADMIN_Permission = ADMIN()


@adapter.property_method("permission")
async def _(bot: Bot, event: Event):
    if await SUPERUSER(bot, event):
        return 3
    elif await OWNER_Permission(bot, event):
        return 2
    elif await ADMIN_Permission(bot, event):
        return 1
    return 0


@adapter.property_method("at")
async def _(bot: Bot, event: Event):
    unimsg: UniMessage[At] = (await get_current_unimsg(bot, event)).get(At)
    return [msg.target for msg in unimsg]


def format_member_info(member: Member, group_id: str) -> MemberInfo:
    nickname = member.user.name or member.user.nick or member.user.id
    return {
        "user_id": member.user.id,
        "group_id": group_id,
        "avatar": member.user.avatar or "",
        "nickname": nickname,
        "card": member.nick or nickname,
        "last_sent_time": 0,
    }


@adapter.call_method("group_member_list")
async def _(group_id: str, /, bot: Bot, event: Event) -> list[MemberInfo]:
    interface = get_interface(bot)
    session = await get_current_session(bot, event)
    if interface is None or session is None:
        return []
    member_list = await interface.get_members(session.scene.type, group_id)
    return [format_member_info(member, group_id) for member in member_list]


@adapter.call_method("group_member_info")
async def _(group_id: str, user_id: str, /, bot: Bot, event: Event) -> MemberInfo:
    interface = get_interface(bot)
    session = await get_current_session(bot, event)
    if interface is None or session is None:
        raise ValueError(f"Can't find member:{group_id}-{user_id}")
    member = await interface.get_member(session.scene.type, scene_id=group_id, user_id=user_id)
    if member is None:
        raise ValueError(f"Can't find member:{group_id}-{user_id}")
    return format_member_info(member, group_id)


__adapter__ = adapter

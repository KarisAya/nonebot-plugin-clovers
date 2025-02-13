import sys
from pathlib import Path
import tomllib

with open("pyproject.toml", "rb") as f:
    nbproject = tomllib.load(f)["tool"]["nonebot"]


def check_file(file: Path):
    if file.exists():
        if input(f"{file} 已存在,是否覆盖？Y/N").upper() != "Y":
            sys.exit(0)
    return file


while priority := input("请输入 clovers 优先级(默认为 20): "):
    if not priority:
        priority = 20
        break
    if priority.isdigit():
        priority = int(priority)
        break
    else:
        print("优先级必须为数字")

connect_to_the_clovers = f"""
# connect_to_the_clovers.py
from nonebot import on_message, get_driver
from nonebot.matcher import Matcher
from nonebot_plugin_clovers import clovers, extract_command

driver = get_driver()
main = on_message(priority={priority}, block=False)
"""

adapters = {adapter["module_name"] for adapter in nbproject["adapters"]}


if "nonebot.adapters.onebot.v11" in adapters:
    response_code = """
from nonebot.adapters.onebot.v11 import Bot as OnebotV11Bot, MessageEvent as OnebotV11Event
from nonebot_plugin_clovers.adapters.onebot.v11 import adapter as onebot_v11_adapter

clovers.register_adapter(onebot_v11_adapter)
onebot_v11 = clovers.leaf(onebot_v11_adapter.name)
driver.on_startup(onebot_v11.startup)
driver.on_shutdown(onebot_v11.shutdown)


@main.handle()
async def _(bot: OnebotV11Bot, event: OnebotV11Event, matcher: Matcher):
    message = extract_command(event.get_plaintext())
    if await onebot_v11.response(message, bot=bot, event=event):
        matcher.stop_propagation()
"""
    connect_to_the_clovers += response_code
if "nonebot.adapters.satori" in adapters:
    response_code = """
from nonebot.adapters.satori import Bot as SatoriBot
from nonebot.adapters.satori.event import MessageCreatedEvent as SatoriEvent
from nonebot_plugin_clovers.adapters.satori import adapter as satori_adapter

clovers.register_adapter(satori_adapter)
satori = clovers.leaf(satori_adapter.name)
driver.on_startup(satori.startup)
driver.on_shutdown(satori.shutdown)


@main.handle()
async def _(bot: SatoriBot, event: SatoriEvent, matcher: Matcher):
    message = extract_command(event.get_plaintext())
    if await satori.response(message, bot=bot, event=event):
        matcher.stop_propagation()
"""
    connect_to_the_clovers += response_code

if "nonebot.adapters.qq" in adapters:
    response_code = """
from nonebot.adapters.qq import Bot as QQBot
from nonebot.adapters.qq import GroupAtMessageCreateEvent as QQGroupEvent
from nonebot_plugin_clovers.adapters.qq.group import adapter as qq_group_adapter

clovers.register_adapter(qq_group_adapter)
qq_group = clovers.leaf(qq_group_adapter.name)
driver.on_startup(qq_group.startup)
driver.on_shutdown(qq_group.shutdown)


@main.handle()
async def _(bot: QQBot, event: QQGroupEvent, matcher: Matcher):
    message = extract_command(event.get_plaintext())
    if await qq_group.response(message, bot=bot, event=event):
        matcher.stop_propagation()


from nonebot.adapters.qq import AtMessageCreateEvent as QQGuildEvent
from nonebot_plugin_clovers.adapters.qq.guild import adapter as qq_guild_adapter

clovers.register_adapter(qq_guild_adapter)
qq_guild = clovers.leaf(qq_guild_adapter.name)
driver.on_startup(qq_guild.startup)
driver.on_shutdown(qq_guild.shutdown)


@main.handle()
async def _(bot: QQBot, event: QQGuildEvent, matcher: Matcher):
    message = extract_command(event.get_plaintext())
    if await qq_guild.response(message, bot=bot, event=event):
        matcher.stop_propagation()
"""
check_file(Path(nbproject["plugin_dirs"][0]) / "connect_to_the_clovers.py").write_text(connect_to_the_clovers)
import os

if os.name != "nt":
    run_sh = check_file(Path("run.sh"))
    run_sh.chmod(0o755)
else:
    run_sh = check_file(Path("run.bat"))

run_sh.write_text("nb run")

CONFIG_FILE = os.environ.get("CLOVERS_CONFIG_FILE", "clovers.toml")

check_file(Path(CONFIG_FILE)).write_text('[clovers]\nplugin_dirs = ["clovers_library/plugins"]')

temp_plugin = check_file(Path("clovers_library/plugins/save_config.py"))
temp_plugin.parent.mkdir(parents=True, exist_ok=True)
temp_plugin.write_text(
    """
from clovers import Plugin
from clovers.logger import logger
from clovers.config import config as clovers_config

plugin = Plugin()


@plugin.startup
async def _():
    clovers_config.save()
    logger.info("clovers 配置已保存。")
    logger.warning(f"本插件由小叶子配置环境脚本生成，请首次执行后删除。\n{__file__}")

__plugin__ = plugin
"""
)

os.system("nb self install -r requirements.txt")

input("环境配置完毕！请手动运行一次 nb run 以生成配置文件。")

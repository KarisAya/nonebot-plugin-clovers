import sys
from pathlib import Path
import tomllib

if __name__ != "__main__":
    raise RuntimeError(f"请不要导入本脚本:{__file__}")

with open("pyproject.toml", "rb") as f:
    nbproject = tomllib.load(f)["tool"]["nonebot"]


def check_file(file: Path):
    if file.exists():
        if input(f"{file} 已存在,是否覆盖？Y/N:").upper() != "Y":
            sys.exit(0)
    return file


while True:
    priority = input("请输入 clovers 优先级(默认为 20): ")
    if not priority:
        priority = 20
        break
    if priority.isdigit():
        priority = int(priority)
        break
    else:
        print("优先级必须为数字")

print(f"正在生成 NoneBot 插件 connect_to_the_clovers , 优先级为 {priority}")

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
    print(f"connect_to_the_clovers 已连接适配器 nonebot.adapters.onebot.v11")
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
    print(f"connect_to_the_clovers 已连接适配器 nonebot.adapters.satori")

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
    connect_to_the_clovers += response_code
    print(f"connect_to_the_clovers 已连接适配器 nonebot.adapters.qq")

check_file(Path(nbproject["plugin_dirs"][0]) / "connect_to_the_clovers.py").write_text(connect_to_the_clovers, encoding="utf-8")

print(f"正在创建启动bot脚本")

import os

if os.name != "nt":
    run_sh = check_file(Path("启动bot.sh"))
    run_sh.chmod(0o755)
else:
    run_sh = check_file(Path("启动bot.bat"))

run_sh.write_text("nb run", encoding="utf-8")

print(f"正在生成clovers配置文件")

CONFIG_FILE = os.environ.get("CLOVERS_CONFIG_FILE", "clovers.toml")

print(f"配置加载插件")
plugins = []
with open("requirement.txt", "r") as file:
    for line in file:
        package = line.strip()
        if package.startswith("clovers"):
            plugin = package.split("==")[0].split(">")[0].split("<")[0].split(">=")[0].split("<=")[0].replace("-", "_")
            print(f"\t{plugin}")
            plugins.append(plugin)

print("以上依据 requirement.txt 添加，如声明有误请手动修改。")

check_file(Path(CONFIG_FILE)).write_text(f'[clovers]\nplugins = {plugins}\nplugin_dirs = ["clovers_library/plugins"]', encoding="utf-8")

temp_plugin = check_file(Path("clovers_library/plugins/save_config.py"))
temp_plugin.parent.mkdir(parents=True, exist_ok=True)
temp_plugin.write_text(
    """from clovers import Plugin
from clovers.logger import logger
from clovers.config import config as clovers_config

plugin = Plugin()


@plugin.startup
async def _():
    clovers_config.save()
    logger.info("clovers 配置已保存。")
    logger.warning(f"本插件由小叶子配置环境脚本生成，请在首次执行后删除。{__file__}")

__plugin__ = plugin""",
    encoding="utf-8",
)

print(f"已创建插件{temp_plugin}")

input("请使用当前环境执行 pip install -r requirement.txt 安装依赖，按任意键退出此脚本")

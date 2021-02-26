import time
import math
from mcdreforged.api.all import *

PLUGIN_METADATA = {
    'id': 'TPN',
    'version': '1.0.0',
    'name': 'TP New',  # RText component is allowed
    'description': 'New Tp assistant for MCDR 1.x',  # RText component is allowed
    'author': 'hyf3513',
    'link': 'https://github.com',
    'dependencies': {
        'mcdreforged': '>=1.0.0',
        'minecraft_data_api': '*'
    }
}

PREFIX = "!!tp"
errMsg = {
    0: "§e没有找到对应的TP请求§r",
    1: "§e没有找到对应发起人§r",
    2: "§e没有找到对应的接收人§r",
    3: "您发起的§e请求§r仍在§6等待确认§r",
    4: "接收方有§6未确认§r的§e请求§r",
    5: "§e您有§6正在处理§r的请求§r",
    6: "§e接收方有§6正在处理§r的请求§r"
}
userlist = []
tpQueue = []


# 实用小工具
# 倒计时器
def timeCounter(secs):
    while secs > 0:
        time.sleep(1)
        secs -= 1


# tp执行模块
@new_thread("newThread")
def tpAfterSeconds(server, name, to, secs=5):
    server.tell(name, f"§2§l{to}§r已经§2同意§r您的请求")
    server.tell(to, f"§2§l{name}§r 将于{secs}s后传送到§b§l{to}§r")
    server.tell(name, f"§2§l{name}§r 将于{secs}s后传送到§b§l{to}§r")
    while secs > 0:
        timeCounter(1)
        server.tell(name, f"§6§lTP countdown {secs}s§r")
        server.tell(to, f"§6§lTP countdown {secs}s§r")
        secs -= 1
    server.tell(name, "§e§o§lTP start!§r")
    server.tell(to, "§e§o§lTP start!§r")
    timeCounter(1)
    cmd = f"/tp {name} {to}"
    print(cmd)
    server.execute(cmd)
    return 0


# 加工帮助信息
def print_message(server, info, msg, tell=True, prefix='[TPN] '):
    msg = prefix + msg
    if info.is_player and not tell:
        server.say(msg)
    else:
        server.reply(info, msg)


# 显示帮助
def showHelp(server, info):
    print_message(server, info, f'{PREFIX} §2§l <玩家> §r | 请求传送到 §b§l <玩家> §的位置')
    print_message(server, info, f'{PREFIX} §2§l <玩家> §r <yes/no> | 对传送请求进行拒绝或者同意')
    print_message(server, info, f'{PREFIX} list 获取当前§3在线玩家§r列表')


# 显示错误
def showErr(server, info, errCode):
    print_message(server, info, f"{PREFIX}+{errMsg.get(errCode)}")


# 命令解析与控制模块
@new_thread("commandParser")
def commandParser(server, info):
    command = info.content.split(" ")
    if command[0] != PREFIX:
        return 0
    if len(command) <= 1:
        showHelp(server, info)
    elif len(command) == 2:
        if command[1] in userlist:
            if checkReqlist(info.player, command[1]) == 0:
                creatReq(server, info.player, command[1])
            elif checkReqlist(info.player, command[1]) == 1:
                showErr(server, info, 3)
            elif checkReqlist(info.player, command[1]) == 2:
                showErr(server, info, 4)
            elif checkReqlist(info.player, command[1]) == -1:
                showErr(server, info, 5)
            elif checkReqlist(info.player, command) == -2:
                showErr(server, info, 6)
        elif command[1] == "help":
            showHelp(server, info)
        elif command[1] == "list":
            server.tell(info.player, userlist)
        else:
            showErr(server, info, 2)
    elif len(command) == 3:
        name = command[1]
        to = info.player
        if name in userlist:
            if command[2] == "yes":
                changeReqStatus(name, to, "yes")
                return 0
            elif command[2] == "no":
                changeReqStatus(name, to, "no")
                return 0
            else:
                showHelp(server, info)
        else:
            showErr(server, info, 1)
    return 0


# 分析tp队列
def checkReqlist(name, to):
    # 双方没有tp请求      return 0
    # 发起方有未完成tp请求 return 1
    # 接收方有未完成tp请求 return 2
    # 发起方有处理中请求   return -1
    # 接收方有处理中请求   return -2

    for tp in tpQueue:
        if tp.get("name") == name and tp.get("status") == "wait":
            return 1
        elif tp.get("to") == to and tp.get("status") == "wait":
            return 2
        elif tp.get("name") == name and tp.get("to") == to and tp.get("status") == "yes":
            return "yes"
        elif tp.get("name") == name and tp.get("to") == to and tp.get("status") == "no":
            return "no"
        elif tp.get("name") == name:
            return -1
        elif tp.get("to") == to:
            return -2
    return 0


# 更改tp列表中的某一行状态
def changeReqStatus(name, to, status):
    for tp in tpQueue:
        if tp.get("name") == name and tp.get("to") == to:
            tp.update({"status": status})
    return 0


# 删除tp队列中的一项
def removeReq(name, to):
    for tp in tpQueue:
        if tp.get("name") == name and tp.get("to") == to:
            tpQueue.remove(tp)
    return 0


# 添加一项到tp队列中

def creatReq(server, name, to):
    api = server.get_plugin_instance('minecraft_data_api')
    topos = api.get_player_coordinate(to)
    namepos = api.get_player_coordinate(name)
    confirmTime = 30
    tpsecs = 5
    tpQueue.append(
        {
            "name": name,
            "to": to,
            "status": "wait"
        })
    while confirmTime > 0:
        timeCounter(2)
        # 获取玩家位置信息
        topos = api.get_player_coordinate(to)
        toposx = math.floor(topos.x)
        toposy = math.floor(topos.y)
        toposz = math.floor(topos.z)
        namepos = api.get_player_coordinate(name)
        nameposx = math.floor(namepos.x)
        nameposy = math.floor(namepos.y)
        nameposz = math.floor(namepos.z)
        server.tell(name, f"tp请求已经传至§b§l{to}§r 坐标： [{toposx},{toposy},{toposz}] ,正在等待确认，剩余时间§3§l{confirmTime}s §r \n")
        server.tell(to,
                    f"§2§l{name} §r 坐标：[{nameposx},{nameposy},{nameposz}] 正在请求传送至你的身边，请输入§2§l!!tp {name} yes §r进行§2§l请求接受§r.\n")
        server.tell(to, f"§4§l输入!!tp {name} no §r将会§4§l拒绝请求 §r\n剩余确认时间：{confirmTime} s\n")
        if checkReqlist(name, to) == "yes":
            tpAfterSeconds(server, name, to, tpsecs)
            removeReq(name, to)
            return 0
        elif checkReqlist(name, to) == "no":
            server.tell(name, f"§4§l{to}拒绝了您的请求§r")
            removeReq(name, to)
            return 0
        confirmTime -= 2

    server.tell(name, "§4请求超时§r")
    server.tell(to, "§4请求超时§r")
    removeReq(name, to)


# MCDR 事件监听器
def on_user_info(server, info):
    commandParser(server, info)


# 用于获取在线用户列表
def on_player_joined(server, player, info):
    if player not in userlist:
        userlist.append(player)


def on_player_left(server, player):
    if player in userlist:
        userlist.remove(player)


def on_load(server, old):
    global userlist
    if old is not None and hasattr(old, 'userlist'):
        userlist = old.userlist
    else:
        userlist = []


def on_server_stop(server, return_code):
    global userlist
    userlist = []

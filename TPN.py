import time
import math
import json
import os
from mcdreforged.api.all import *

PLUGIN_METADATA = {
    'id': 'TPN',
    'version': '1.3.0',
    'name': 'TP New',
    'description': 'New Tp assistant for MCDR 1.x',
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
    6: "§e接收方有§6正在处理§r的请求§r",
    7: "§c home坐标文件读取错误§r",
    8: "还未设定§6home坐标§r，请先执行§b§l !!tp home set §r"
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
    print_message(server, info, f'{PREFIX} home §a一键回家§r')
    print_message(server, info, f'{PREFIX} home set 设置§b回家坐标§r')


# 显示错误
def showErr(server, info, errCode):
    print_message(server, info, f"{PREFIX}+{errMsg.get(errCode)}")


# 命令解析与控制模块
@new_thread("commandParser")
def commandParser(server, info):
    flag = ""
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
            get_userlist(server,info)
            server.tell(info.player,userlist)
        elif command[1] == "home":
            tpHome(server, info)
        else:
            showErr(server, info, 2)
    elif len(command) == 3:
        if command[1] in userlist:
            name = command[1]
            to = info.player
            if command[2] == "yes":
                changeReqStatus(name, to, "yes")
                return 0
            elif command[2] == "no":
                changeReqStatus(name, to, "no")
                return 0
            else:
                showHelp(server, info)
        elif command[2] == "set" and command[1] == "home":
            setHome(server, info)
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


# 获取home坐标
def getHome(server, info):
    player = info.player
    try:
        with open("./plugins/homepos.json", "r") as f:
            jsonR = json.load(f)
            for item in jsonR:
                if item.get("name") == player:
                    pos = item.get("pos")
                    server.say(pos)
                    return pos
                else:
                    showErr(server, info, 8)
                    return -1

    except:
        showErr(server, info, 7)
        return -1


# 添加/修改home坐标
@new_thread("setHome")
def setHome(server, info):
    flag = ""  # 用于标识是被修改还是被添加
    i = 0  # 用于标识读取json数组
    player = info.player
    if player in userlist:
        api = server.get_plugin_instance("minecraft_data_api")
        pos = api.get_player_coordinate(player)

        if not os.path.exists("./plugins/homepos.json"):
            with open("./plugins/homepos.json", "w+") as f:
                f.writelines("[]")
                server.say("home数据文件已经初始化")
        try:
            with open("./plugins/homepos.json", "r") as f:
                server.tell(player, "正在§9§l读取位置文件§r")
                try:
                    jsonR = json.load(f)
                except:
                    pass
                else:
                    if jsonR != {}:
                        for item in jsonR:
                            if item.get("name") == player:
                                server.tell(player, "\n正在§a§l修改位置文件§r")
                                jsonR[i]["pos"] = [pos.x, pos.y, pos.z]
                                flag = "edited"
                        i += 1
            if flag != "edited":
                Nitem = {}
                Nitem["name"] = player
                Nitem["pos"] = [pos.x, pos.y, pos.z]
                server.say(Nitem)
                jsonR.append(Nitem)
                server.tell(player, "正在§a§l新建位置§r")
                server.tell(player, "§a§l新建位置§r完成！")
            try:
                with open("./plugins/homepos.json", "w") as f:
                    json.dump(jsonR, f)
            except:
                showErr(server, info, 7)


        except:
            showErr(server, info, 7)
            return -1

    return 0


# 执行回home
def tpHome(server, info):
    player = info.player
    if player in userlist:
        homePos = getHome(server, info)
        posX = homePos[0]
        posY = homePos[1]
        posZ = homePos[2]
        server.tell(player, f"即将回家! §2§l{homePos}§r ")
        cmd = f"/tp {player} {posX} {posY} {posZ}"
        server.execute(cmd)
        return 0
    else:
        return -1


# MCDR 事件监听器
def on_user_info(server, info):
    get_userlist(server,info)
    commandParser(server, info)


# 利用MinecraftDataAPI来获取用户列表
@new_thread("getPlayerlist")
def get_userlist(server,info):
    global user_amount, user_limit, userlist
    api = server.get_plugin_instance('minecraft_data_api')
    user_amount, user_limit, userlist = api.get_server_player_list()





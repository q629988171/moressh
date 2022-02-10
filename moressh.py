import asyncio
import json

import asyncssh
import pandas as pandas
from loguru import logger
from tqdm import tqdm


def format_message(msg):
    """格式化消息字符串

    :param msg: 消息字符串
    :return: 错误代码, 错误说明
    """
    if len(msg) >= 2:
        errcode = msg[0]
        errmsg = msg[1]
    else:
        errcode = -1
        errmsg = msg[0]
    return errcode, errmsg


def get_jumphosts(file):
    """加载json格式配置文件

    :param file: json文件名
    :return: json格式数据

    """
    with open(file, "r") as f:
        json_data = json.load(f)
        return json_data


def import_cvs(filepath):
    """导入 cvs文件

    :param filepath: 文件路径
    :return: JSON字符串
    """
    df = pandas.read_csv(filepath)
    # 创建按行方向的JSON字符串
    df_json = df.to_json(orient='records')
    return df_json


def get_hosts(data):
    """将字符串转化为字典

    :param data: JSON字符串
    :return: 主机信息(字典)
    """
    hosts = json.loads(data)
    return hosts


async def ssh_connect(jumphost=None, *args, **kwargs):
    """

    :param jumphost: 跳板机
    :param args: 主机信息
    :param kwargs: 跳板机信息
    :return: SSH对象
    """

    if jumphost:
        tunnel = await asyncssh.connect(kwargs['jump_host'], kwargs['jump_port'], username=kwargs['jump_username'],
                                        password=kwargs['jump_password'], known_hosts=None)
        conn = await tunnel.connect_ssh(args[0], args[1], username=args[2], password=args[3],
                                        known_hosts=None)
    else:
        conn = await asyncssh.connect(args[0], args[1], username=args[2], password=args[3], known_hosts=None)
    return conn


async def run_commands(jumphost=None, *args, **kwargs):
    """执行多个命令

    :param jumphost: 跳板机
    :param args: 主机信息
    :param kwargs: 跳板机信息
    :return: 执行结果
    """
    results = []
    commands = args[4].split(';')
    try:
        conn = await ssh_connect(jumphost, *args, **kwargs)
        async with conn:
            # 执行SSH命令
            for command in commands:
                result = await conn.run(command, check=True)
                results.append(result.stdout)
            return 0, results

    except Exception as e:
        message = format_message(e.args)
        errcode, errmsg = message[0], message[1]
        return errcode, errmsg


async def run_command(host_conf, jumphost_conf):
    """执行命令

    :param jumphost_conf: 跳板机信息(json)
    :param host_conf: 主机信息(字典)
    """
    host = host_conf.get('host', '127.0.0.1')
    port = host_conf.get('port', 22)
    username = host_conf.get('username', 'admin')
    password = host_conf.get('password', 'admin')
    commands = host_conf.get('commands', 'whoami')
    jumphost = host_conf.get('jumphost', None)
    logger.info(f"正在连接: {host}:{port}")
    if jumphost:
        result = await run_commands(
            jumphost,
            str(host), port, str(username), str(password), commands,
            jump_host=str(jumphost_conf[jumphost]["host"]),
            jump_port=jumphost_conf[jumphost]["port"],
            jump_username=str(jumphost_conf[jumphost]["username"]),
            jump_password=str(jumphost_conf[jumphost]["password"])
        )
    else:
        result = await run_commands(jumphost, str(host), port, str(username), str(password), commands)

    logger.info(f"连接完成: {host}:{port}, errcode: {result[0]}, errmsg: {result[1]}")


async def parallel_run(hosts, jumphosts):
    """连接多个主机

    :param jumphosts: 跳板机信息(json)
    :param hosts: 主机信息(字典)
    """
    tasks = []
    for host in hosts:
        task = asyncio.create_task(run_command(host, jumphosts))
        tasks.append(task)
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Connect SSH"):
        await f


def main():
    # 移除控制台输出
    # logger.remove(handler_id=None)
    logger.add(sink="logs/moressh_{time}.log", enqueue=True)
    filepath = f"device_list.csv"
    logger.info(f"正在加载: {filepath}")
    data = import_cvs(filepath)
    hosts = get_hosts(data)
    logger.info(f"加载完成: {filepath}")
    jumphosts = get_jumphosts("jumphost.json")
    print('Starting, use <Ctrl-C> to stop')
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(parallel_run(hosts, jumphosts))
    except KeyboardInterrupt:
        asyncio.gather(*asyncio.Task.all_tasks()).cancel()
        loop.stop()


if __name__ == '__main__':
    main()

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


async def ssh_connect(host, port, username, password, known_hosts):
    """连接SSH

    :param host: 主机
    :param port: 端口
    :param username: 用户名
    :param password: 密码
    :param known_hosts: 访问过计算机的公钥
    :return: 连接对象
    """
    conn = await asyncssh.connect(host=str(host), port=port, username=str(username), password=str(password),
                                  known_hosts=known_hosts)
    return conn


async def run_commands(host, port, username, password, known_hosts, commands):
    """执行多个命令

    :param host: 主机
    :param port: 端口
    :param username: 用户名
    :param password: 密码
    :param known_hosts: 访问过计算机的公钥
    :param commands: 命令
    :return: 执行结果
    """
    results = []
    try:
        conn = await ssh_connect(host=str(host), port=port, username=str(username), password=str(password),
                                 known_hosts=known_hosts)
        async with conn:
            # 执行SSH命令
            for command in commands.split(';'):
                result = await conn.run(command, check=True)
                results.append(result.stdout)
            return 0, results

    except Exception as e:
        message = format_message(e.args)
        errcode, errmsg = message[0], message[1]
        return errcode, errmsg


async def run_command(host_conf):
    """执行命令

    :param host_conf: 主机信息(字典)
    """
    host = host_conf.get('host', '127.0.0.1')
    port = host_conf.get('port', 22)
    username = host_conf.get('username', 'admin')
    password = host_conf.get('password', 'admin')
    # 如果机器时第一次SSH登录，需要将known_hosts 设置为None，否在会报错
    known_hosts = host_conf.get('known_hosts', None)
    commands = host_conf.get('commands', 'whoami')
    logger.info(f"正在连接: {host}:{port}")
    result = await run_commands(host, port, username, password, known_hosts, commands)
    logger.info(f"连接完成: {host}:{port}, errcode: {result[0]}, errmsg: {result[1]}")


async def parallel_run(hosts):
    """连接多个主机

    :param hosts: 主机信息(字典)
    """
    tasks = []
    for host in hosts:
        task = asyncio.create_task(run_command(host))
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
    logger.info("加载完成")
    print('Starting, use <Ctrl-C> to stop')
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(parallel_run(hosts))
    except KeyboardInterrupt:
        asyncio.gather(*asyncio.Task.all_tasks()).cancel()
        loop.stop()
    finally:
        loop.close()


if __name__ == '__main__':
    main()

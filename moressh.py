import asyncio
import json
from functools import partial

import asyncssh
import pandas as pandas
from loguru import logger
from tqdm import tqdm


def import_cvs(filepath):
    df = pandas.read_csv(filepath)
    # 创建按行方向的JSON字符串
    df_json = df.to_json(orient='records')
    return df_json


def get_hosts(data):
    # 将字符串转化为字典
    host_list = json.loads(data)
    return host_list


def on_job_done(host_conf, future):
    # 获取主机名
    host = host_conf.get('host', '127.0.0.1')
    # 获取结果
    ret = future.result()
    if len(ret) >= 2:
        errcode = ret[0]
        errmsg = ret[1]
    else:
        errcode = -1
        errmsg = ret[0]
    logger.info(f"连接结束: {host}, errcode: {errcode}, errmsg: {errmsg}")


async def ssh2(host_conf):
    host = host_conf.get('host', '127.0.0.1')
    port = host_conf.get('port', 22)
    username = host_conf.get('username', 'admin')
    password = host_conf.get('password', 'admin')
    # 如果机器时第一次SSH登录，需要将known_hosts 设置为None，否在会报错
    known_hosts = host_conf.get('known_hosts', None)
    command = host_conf.get('command', 'whoami')
    logger.info(f"正在连接: {host}")
    # 初始化一个SSH连接
    try:
        async with asyncssh.connect(
                host=str(host),
                port=port,
                username=str(username),
                password=str(password),
                known_hosts=known_hosts
        ) as conn:
            # 执行SSH命令
            result = await conn.run(command)
            return 0, result.stdout.strip()
    except Exception as e:
        return e.args


async def excutor(host_list):
    tasks = []
    for host in host_list:
        task = asyncio.create_task(ssh2(host))
        tasks.append(task)
        task.add_done_callback(partial(on_job_done, host))
    # await asyncio.gather(*tasks)
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Connect SSH"):
        await f


def main():
    logger.remove(handler_id=None)
    logger.add(sink="logs/moressh_{time}.log", enqueue=True)
    filepath = f"device_list.csv"
    logger.info(f"正在加载: {filepath}")
    data = import_cvs(filepath)
    host_list = get_hosts(data)
    logger.info("加载完成")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(excutor(host_list))
    finally:
        loop.close()


if __name__ == '__main__':
    main()

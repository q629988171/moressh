# 简介

从 csv 文件导入HOST信息, 连接SSH, 执行命令

## 使用说明

1. 安装依赖库: pip install -r requirements.txt
2. 编辑 device_list.csv
3. python moressh.py

## 跳板机使用说明

1. 编辑 jumphost.json, 添加跳板机.
2. 编辑 device_list.csv->"jumphost" 字段, 添加跳板机名称.
3. 没有跳板机只需保持 device_list.csv->"jumphost" 字段为空.

## 特性

- 批量执行
- 异步并发
- 写入日志
- 多个命令
- 跳板机连接

## 注意

仅支持linux主机, 其他类型设备可能会有问题.

## todo

- [X] ctrl+c 终止连接
- [X] 通过跳板机连接

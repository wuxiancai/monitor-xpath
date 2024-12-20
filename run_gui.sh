#!/bin/bash

# 激活虚拟环境
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "错误: 激活虚拟环境失败"
    exit 1
fi

# 运行GUI程序
echo "启动GUI监控程序..."
python3 gui.py

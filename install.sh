#!/bin/bash

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3,请先安装Python3"
    exit 1
fi

# 使用Python自身检查版本
PYTHON_VERSION_CHECK=$(python3 -c '
import sys
if sys.version_info >= (3, 7):
    print("1")
else:
    print("0")
')

if [ "$PYTHON_VERSION_CHECK" != "1" ]; then
    echo "错误: Python版本必须 >= 3.7"
    exit 1
fi

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "错误: 未找到pip3,请先安装pip3"
    exit 1
fi

# 检查tkinter
python3 -c "import tkinter" 2>/dev/null || {
    echo "错误: 未找到tkinter,请安装python3-tk"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "在macOS上安装tkinter: brew install python-tk"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "在Ubuntu/Debian上安装tkinter: sudo apt-get install python3-tk"
        echo "在CentOS/RHEL上安装tkinter: sudo yum install python3-tkinter"
    fi
    exit 1
}

# 在macOS上安装系统依赖
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到macOS系统，正在检查必要的系统依赖..."
    
    # 检查是否安装了homebrew
    if ! command -v brew &> /dev/null; then
        echo "未检测到Homebrew，正在自动安装..."
        
        # 下载并执行Homebrew安装脚本
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
            echo "错误: Homebrew安装失败"
            exit 1
        }
        
        # 设置Homebrew环境变量
        if [[ $(uname -m) == 'arm64' ]]; then
            # M1/M2 Mac
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            # Intel Mac
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi
        
        echo "Homebrew安装完成"
    fi
    
    # 安装Chrome浏览器
    echo "检查Chrome浏览器..."
    if ! command -v google-chrome &> /dev/null; then
        echo "安装Chrome浏览器..."
        brew install --cask google-chrome
    fi
    
    # 安装libxml2和libxslt
    echo "安装libxml2和libxslt..."
    brew install libxml2 libxslt || {
        echo "错误: 安装libxml2和libxslt失败"
        exit 1
    }
    
    # 设置环境变量
    if [[ $(uname -m) == 'arm64' ]]; then
        # M1/M2 Mac
        export LDFLAGS="-L/opt/homebrew/opt/libxml2/lib -L/opt/homebrew/opt/libxslt/lib"
        export CPPFLAGS="-I/opt/homebrew/opt/libxml2/include -I/opt/homebrew/opt/libxslt/include"
    else
        # Intel Mac
        export LDFLAGS="-L/usr/local/opt/libxml2/lib -L/usr/local/opt/libxslt/lib"
        export CPPFLAGS="-I/usr/local/opt/libxml2/include -I/usr/local/opt/libxslt/include"
    fi
fi

# 创建虚拟环境
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "错误: 创建虚拟环境失败"
        exit 1
    fi
fi

# 激活虚拟环境
source $VENV_DIR/bin/activate
if [ $? -ne 0 ]; then
    echo "错误: 激活虚拟环境失败"
    exit 1
fi

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # 在macOS上单独安装lxml
    echo "安装lxml..."
    STATIC_DEPS=true pip3 install lxml selenium webdriver-manager || {
        echo "错误: 安装lxml失败"
        exit 1
    }
    
    # 安装其他依赖
    echo "安装其他依赖..."
    pip3 install requests schedule pyyaml || {
        echo "错误: 安装其他依赖失败"
        exit 1
    }
else
    pip3 install -r requirements.txt || {
        echo "错误: 安装依赖失败"
        exit 1
    }
fi

# 创建命令行运行脚本
echo "创建运行脚本..."
cat > run.sh << 'EOF'
#!/bin/bash

# 激活虚拟环境
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "错误: 激活虚拟环境失败"
    exit 1
fi

# 运行程序
echo "启动监控程序..."
python3 monitor.py
EOF

# 创建GUI运行脚本
cat > run_gui.sh << 'EOF'
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
EOF

# 设置执行权限
chmod +x run.sh
chmod +x run_gui.sh

echo "安装完成!"
echo "使用 ./run.sh 运行命令行版本"
echo "使用 ./run_gui.sh 运行GUI版本"


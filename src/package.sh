# 进入当前脚本目录
cd $(dirname $0)
# 清理缓存（删除构建和生成目录）
rm -rf build dist

# 激活Python虚拟环境
# source ../.venv3_8/bin/activate
source ../.venv3_9/bin/activate

# 打包
# pyinstaller --onefile itubego-dl.py -p ../src
pyinstaller --onefile --target-arch x86_64 itubego-dl.py -p ../src

# 混淆加密
# pyarmor gen -O obfdist --pack dist/itubego-dl itubego-dl.py
arch -x86_64 pyarmor gen --pack dist/itubego-dl -r itubego-dl.py my_get

#注意：该脚本文件需在勾选 Rosetta 的terminal执行，否则指定 x86 报错

#!/bin/sh
set -e

# 打印欢迎信息
echo "启动Yacd-meta服务..."

# 确保配置目录存在并设置正确权限
mkdir -p /root/.config/clash
chmod -R 777 /root/.config/clash

# 设置配置文件路径环境变量
export CLASH_CONFIG_PATH="/root/.config/clash/config.yaml"

# 设置默认的Clash API URL环境变量（仅用于初始显示）
# Python后端将自动根据请求动态生成实际的API地址
if [ -z "$YACD_DEFAULT_BACKEND" ]; then
    echo "未设置YACD_DEFAULT_BACKEND，初始值将自动生成"
    export YACD_DEFAULT_BACKEND="auto"
else
    echo "使用环境变量设置的Clash API URL: $YACD_DEFAULT_BACKEND"
fi

# 将YACD_DEFAULT_BACKEND注入到Nginx配置中用于初始界面显示
sed -i "s|__YACD_DEFAULT_BACKEND__|$YACD_DEFAULT_BACKEND|g" /etc/nginx/conf.d/default.conf

# 打印环境信息
echo "配置文件路径: /root/.config/clash/config.yaml"
echo "订阅服务端口: 7888"
echo "Web界面端口: 80"

# 启动Nginx
echo "启动Nginx服务..."
nginx

# 启动Python应用
echo "启动Python订阅服务..."
cd /app
python app.py

# 实际上我们不会到达这里，因为Python应用会持续运行
# 但为了完整性，我们添加了这个处理程序
exec "$@"

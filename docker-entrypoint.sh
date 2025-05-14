#!/bin/sh
# Replace backend URL in index.html
sed -i "s|http://127.0.0.1:9090|$YACD_DEFAULT_BACKEND|" /usr/share/nginx/html/index.html

# 调试信息
echo "配置Nginx和Python环境..."
# 确保配置目录存在
mkdir -p /root/.config/clash
mkdir -p /app/python

# 创建一个测试配置文件以确保权限正确
echo "# 测试配置" > /app/python/config.yaml
chmod 666 /app/python/config.yaml
echo "配置文件权限已设置"

# 调试信息
echo "启动Nginx服务..."
# Start Nginx in background
nginx

# 调试信息
echo "等待Nginx启动完成..."
sleep 2

# 调试信息
echo "启动Python应用..."
# Start Python application in the foreground
cd /app && python app.py

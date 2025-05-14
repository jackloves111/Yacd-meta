#!/bin/sh
# Replace backend URL in index.html
sed -i "s|http://127.0.0.1:9090|$YACD_DEFAULT_BACKEND|" /usr/share/nginx/html/index.html

# 调试信息
echo "配置Nginx和Python环境..."
# 确保配置目录存在
mkdir -p /root/.config/clash

# 调试信息
echo "检查默认配置文件是否存在..."
# 如果配置文件不存在，创建一个空的配置文件
if [ ! -f "/root/.config/clash/config.yaml" ]; then
    echo "# SUBSCRIBE_URL: " > /root/.config/clash/config.yaml
    echo "创建了空的配置文件"
fi

# 检查配置文件是否有订阅地址
if ! grep -q "SUBSCRIBE_URL" /root/.config/clash/config.yaml; then
    # 如果没有订阅地址标记，添加一个
    sed -i '1i# SUBSCRIBE_URL: ' /root/.config/clash/config.yaml
    echo "添加了订阅地址标记"
fi

# 确保配置文件权限正确
chmod 666 /root/.config/clash/config.yaml
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

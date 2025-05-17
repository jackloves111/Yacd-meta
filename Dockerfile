# 第一阶段：构建前端
FROM --platform=$BUILDPLATFORM node:alpine AS builder-frontend
WORKDIR /app
COPY . .
RUN npm i -g pnpm \
    && pnpm i \
    && pnpm build \
    # 移除source map文件以减小镜像体积
    && rm public/*.map || true

# 第二阶段：准备Python后端及最终镜像
FROM python:3.9-alpine

# 复制Nginx配置文件
COPY docker/default.conf /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf /etc/nginx/nginx.conf

WORKDIR /app

# 设置Python环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装Nginx及其他工具
RUN apk add --no-cache nginx dos2unix

# 复制并安装Python依赖
COPY python/ .
RUN pip install --no-cache-dir -r requirements.txt

# 创建Clash配置目录并设置适当权限
RUN mkdir -p /root/.config/clash && \
    chmod -R 777 /root/.config/clash

# 移除默认Nginx内容并复制构建好的前端资源
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder-frontend /app/public /usr/share/nginx/html

# 设置YACD默认后端URL（可在运行时覆盖）
ENV YACD_DEFAULT_BACKEND "http://127.0.0.1:9090"

# 仅暴露Nginx端口(80)
EXPOSE 80

# 复制并准备入口点脚本
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh && dos2unix /docker-entrypoint.sh

# 运行入口点脚本的命令
CMD ["/docker-entrypoint.sh"]
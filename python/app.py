import os
import re
import requests
import subprocess
import logging
from flask import Flask, render_template, request, jsonify, url_for

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_url_path='/static')

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
CLASH_CONFIG_PATH = '/root/.config/clash/config.yaml'

@app.route('/')
def index():
    """渲染主页"""
    logger.info("访问订阅页面")
    return render_template('index.html')

@app.route('/update_config', methods=['POST'])
def update_config():
    """更新配置文件"""
    try:
        # 获取订阅URL
        subscribe_url = request.form.get('subscribe_url')
        logger.info(f"收到订阅更新请求，URL: {subscribe_url}")
        
        if not subscribe_url:
            logger.error("订阅地址为空")
            return jsonify({"status": "error", "message": "订阅地址不能为空"}), 400
        
        # 确保URL末尾有clash标志
        if '&flag=clash' not in subscribe_url and '?flag=clash' not in subscribe_url:
            if '?' in subscribe_url:
                subscribe_url += '&flag=clash'
            else:
                subscribe_url += '?flag=clash'
        
        logger.info(f"处理后的订阅URL: {subscribe_url}")
        
        # 下载配置文件
        logger.info("正在下载配置文件...")
        response = requests.get(subscribe_url)
        if response.status_code != 200:
            logger.error(f"下载失败，状态码: {response.status_code}")
            return jsonify({"status": "error", "message": f"下载订阅配置失败，HTTP状态码: {response.status_code}"}), 500
        
        # 保存配置文件
        with open(CONFIG_FILE, 'wb') as f:
            f.write(response.content)
        logger.info(f"配置文件已保存到: {CONFIG_FILE}")
        
        # 修改配置文件
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换配置
        content = re.sub(r'mixed-port: 7890', 'port: 7890\nsocks-port: 7891', content)
        content = re.sub(r"external-controller: '127.0.0.1:9090'", "external-controller: '0.0.0.0:9090'", content)
        
        # 保存修改后的配置
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info("配置文件已修改")
        return jsonify({"status": "success", "message": "订阅配置更新成功"})
    
    except Exception as e:
        logger.error(f"发生异常: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": f"更新失败: {str(e)}"}), 500

@app.route('/get_config')
def get_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取配置文件失败: {str(e)}")
        return "当前没有可用配置", 404

if __name__ == '__main__':
    logger.info("Python 订阅应用启动在 0.0.0.0:7888")
    app.run(host='0.0.0.0', port=7888, debug=False)
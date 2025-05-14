import os
import re
import requests
import subprocess
import logging
from flask import Flask, render_template, request, jsonify, url_for
from flask_cors import CORS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_url_path='/static')
# 启用CORS
CORS(app)

# 配置文件路径 - 使用绝对路径确保一致性
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CURRENT_DIR, 'config.yaml')
CLASH_CONFIG_PATH = '/root/.config/clash/config.yaml'

# 确保配置目录存在
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

@app.route('/')
def index():
    """渲染主页"""
    logger.info("访问订阅页面")
    return render_template('index.html')

@app.route('/update_config', methods=['POST', 'OPTIONS'])
def update_config():
    """更新配置文件"""
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        logger.info("收到OPTIONS预检请求")
        return '', 204

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
        try:
            response = requests.get(subscribe_url, timeout=30)
            response.raise_for_status()  # 检查HTTP错误
        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败，异常: {str(e)}")
            return jsonify({"status": "error", "message": f"下载订阅配置失败: {str(e)}"}), 500
        
        # 保存配置文件
        try:
            with open(CONFIG_FILE, 'wb') as f:
                f.write(response.content)
            logger.info(f"配置文件已保存到: {CONFIG_FILE}")
            
            # 复制到Clash配置目录（如果需要）
            try:
                os.makedirs(os.path.dirname(CLASH_CONFIG_PATH), exist_ok=True)
                with open(CLASH_CONFIG_PATH, 'wb') as clash_file:
                    clash_file.write(response.content)
                logger.info(f"配置文件已复制到Clash目录: {CLASH_CONFIG_PATH}")
            except Exception as e:
                logger.warning(f"复制到Clash目录失败: {str(e)}")
                # 这不是致命错误，继续处理
        except IOError as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return jsonify({"status": "error", "message": f"保存配置文件失败: {str(e)}"}), 500
        
        # 修改配置文件
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换配置
            content = re.sub(r'mixed-port: 7890', 'port: 7890\nsocks-port: 7891', content)
            content = re.sub(r"external-controller: '127.0.0.1:9090'", "external-controller: '0.0.0.0:9090'", content)
            
            # 保存修改后的配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("配置文件已修改")
            
            # 检查文件是否存在并且有内容
            if os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
                logger.info(f"配置文件确认存在，大小: {os.path.getsize(CONFIG_FILE)} 字节")
            else:
                logger.error("配置文件不存在或为空")
                return jsonify({"status": "error", "message": "配置文件保存后不存在或为空"}), 500
        except Exception as e:
            logger.error(f"修改配置文件失败: {str(e)}")
            return jsonify({"status": "error", "message": f"修改配置文件失败: {str(e)}"}), 500
            
        logger.info("订阅配置更新成功")
        return jsonify({"status": "success", "message": "订阅配置更新成功"})
    
    except Exception as e:
        logger.error(f"发生异常: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": f"更新失败: {str(e)}"}), 500

@app.route('/get_config')
def get_config():
    """获取配置文件内容"""
    try:
        logger.info(f"尝试读取配置文件: {CONFIG_FILE}")
        if not os.path.exists(CONFIG_FILE):
            logger.warning(f"配置文件不存在: {CONFIG_FILE}")
            return "当前没有可用配置", 404
            
        if os.path.getsize(CONFIG_FILE) == 0:
            logger.warning("配置文件为空")
            return "配置文件为空", 404
            
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"成功读取配置文件，内容长度: {len(content)}")
        return content
    except Exception as e:
        logger.error(f"读取配置文件失败: {str(e)}")
        return f"读取配置失败: {str(e)}", 500

@app.route('/health')
def health_check():
    """健康检查接口"""
    config_exists = os.path.exists(CONFIG_FILE)
    config_size = os.path.getsize(CONFIG_FILE) if config_exists else 0
    
    return jsonify({
        "status": "ok", 
        "message": "服务正常运行",
        "config_file": CONFIG_FILE,
        "config_exists": config_exists,
        "config_size": config_size
    })

if __name__ == '__main__':
    logger.info(f"Python 订阅应用启动在 0.0.0.0:7888，配置文件路径: {CONFIG_FILE}")
    # 确保配置目录存在
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(CLASH_CONFIG_PATH), exist_ok=True)
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=7888, debug=False)
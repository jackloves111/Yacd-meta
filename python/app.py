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

# 配置文件路径 - 使用统一的配置文件路径
CLASH_CONFIG_PATH = '/root/.config/clash/config.yaml'
CONFIG_FILE = CLASH_CONFIG_PATH  # 使用统一的配置文件路径

# 确保配置目录存在
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

def get_subscribe_url_from_config():
    """从配置文件中获取保存的订阅地址"""
    if not os.path.exists(CONFIG_FILE):
        logger.warning("配置文件不存在，无法获取订阅地址")
        return ""
        
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 使用正则表达式从配置文件中提取订阅地址
        # 格式: # SUBSCRIBE_URL: http://example.com
        match = re.search(r'# SUBSCRIBE_URL: (.*?)(\r?\n|$)', content)
        if match and match.group(1).strip():
            logger.info(f"从配置文件中获取到订阅地址: {match.group(1).strip()}")
            return match.group(1).strip()
        
        logger.info("配置文件中未找到有效的订阅地址")
        return ""
    except Exception as e:
        logger.error(f"从配置文件中获取订阅地址失败: {str(e)}")
        return ""

def save_subscribe_url_to_config(subscribe_url, content=None):
    """将订阅地址保存到配置文件"""
    # 移除订阅地址中可能已有的&flag=clash或?flag=clash
    clean_url = re.sub(r'[&?]flag=clash$', '', subscribe_url)
    
    if not os.path.exists(CONFIG_FILE):
        # 如果配置文件不存在，创建一个包含订阅地址的空配置
        logger.info(f"配置文件不存在，创建新文件: {CONFIG_FILE}")
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"# SUBSCRIBE_URL: {clean_url}\n")
            logger.info(f"创建了包含订阅地址的新配置文件: {clean_url}")
            return True
        except Exception as e:
            logger.error(f"创建配置文件失败: {str(e)}")
            return False
        
    try:
        if content is None:
            # 读取现有配置
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # 检查是否已有订阅地址标记
        if re.search(r'# SUBSCRIBE_URL:', content):
            # 更新现有的订阅地址
            new_content = re.sub(r'# SUBSCRIBE_URL: .*?(\r?\n|$)', 
                            f"# SUBSCRIBE_URL: {clean_url}\n", content)
            logger.info(f"更新了现有的订阅地址: {clean_url}")
        else:
            # 在文件开头添加订阅地址
            new_content = f"# SUBSCRIBE_URL: {clean_url}\n" + content
            logger.info(f"添加了新的订阅地址: {clean_url}")
        
        # 保存修改后的配置
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        logger.info(f"订阅地址已保存到配置文件: {clean_url}")
        return True
    except Exception as e:
        logger.error(f"保存订阅地址到配置文件失败: {str(e)}")
        return False

def add_clash_flag_to_url(url):
    """向URL添加flag=clash参数"""
    if not url:
        return url
        
    # 如果已经有flag=clash就不再添加
    if 'flag=clash' in url:
        return url
        
    # 添加flag=clash
    if '?' in url:
        return f"{url}&flag=clash"
    else:
        return f"{url}?flag=clash"

@app.route('/')
def index():
    """渲染主页"""
    logger.info("访问订阅页面")
    return render_template('index.html')

@app.route('/get_subscribe_info')
def get_subscribe_info():
    """获取保存的订阅信息"""
    try:
        subscribe_url = get_subscribe_url_from_config()
        logger.info(f"获取订阅地址API: {subscribe_url}")
        
        # 确保返回有效的JSON响应
        response = {"subscribe_url": subscribe_url}
        return jsonify(response)
    except Exception as e:
        logger.error(f"获取订阅信息失败: {str(e)}")
        return jsonify({"subscribe_url": ""}), 500

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
        
        # 先保存订阅地址，确保地址不会丢失
        # 这里保存原始地址，不添加flag=clash
        save_subscribe_url_to_config(subscribe_url)
        
        # 为下载添加flag=clash
        download_url = add_clash_flag_to_url(subscribe_url)
        logger.info(f"下载用的订阅URL: {download_url}")
        
        # 下载配置文件
        logger.info("正在下载配置文件...")
        try:
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()  # 检查HTTP错误
        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败，异常: {str(e)}")
            return jsonify({"status": "error", "message": f"下载订阅配置失败: {str(e)}"}), 500
        
        # 获取配置内容
        try:
            config_content = response.content.decode('utf-8')
            
            # 保存配置文件前先应用订阅地址
            # 使用原始地址，而不是带flag=clash的
            config_with_url = f"# SUBSCRIBE_URL: {subscribe_url}\n" + config_content
            
            # 直接写入带有订阅地址的配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(config_with_url)
                
            logger.info(f"配置文件(含订阅地址)已保存到: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return jsonify({"status": "error", "message": f"保存配置文件失败: {str(e)}"}), 500
        
        # 修改配置文件
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换配置
            content = re.sub(r'mixed-port: 7890', 'port: 7890\nsocks-port: 7891', content)
            content = re.sub(r"external-controller: '127.0.0.1:9090'", "external-controller: '0.0.0.0:9090'", content)
            
            # 保存修改后的配置，确保订阅地址不丢失
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("配置文件已修改并保存")
            
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
    subscribe_url = get_subscribe_url_from_config()
    
    return jsonify({
        "status": "ok", 
        "message": "服务正常运行",
        "config_file": CONFIG_FILE,
        "config_exists": config_exists,
        "config_size": config_size,
        "subscribe_info": {
            "subscribe_url": subscribe_url
        }
    })

if __name__ == '__main__':
    logger.info(f"Python 订阅应用启动在 0.0.0.0:7888，配置文件路径: {CONFIG_FILE}")
    # 确保配置目录存在
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    # 在启动时记录配置文件状态
    config_exists = os.path.exists(CONFIG_FILE)
    logger.info(f"配置文件存在: {config_exists}")
    
    if config_exists:
        subscribe_url = get_subscribe_url_from_config()
        logger.info(f"当前订阅地址: {subscribe_url}")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=7888, debug=False)
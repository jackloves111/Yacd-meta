import os
import re
import json
import requests
import socket
import logging
import urllib.parse
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

# 默认Clash API端口
DEFAULT_CLASH_PORT = 9090

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

def get_server_ip_from_request():
    """从请求中获取服务器IP地址"""
    # 获取请求的Host头
    host = request.host
    
    # 如果Host头包含端口，则去除端口
    if ':' in host:
        host = host.split(':')[0]
    
    # 检查是否是localhost或127.0.0.1
    if host in ['localhost', '127.0.0.1']:
        # 尝试获取本机的真实IP
        try:
            # 尝试获取主机名对应的IP
            host_ip = socket.gethostbyname(socket.gethostname())
            if not host_ip.startswith('127.'):
                return host_ip
            
            # 如果还是本地IP，尝试通过创建一个socket连接外部来获取
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            host_ip = s.getsockname()[0]
            s.close()
            return host_ip
        except Exception as e:
            logger.warning(f"获取主机IP失败: {str(e)}")
            return host
    
    return host

def get_clash_api_url():
    """根据当前请求获取Clash API地址"""
    # 首先尝试从当前服务器IP构建API地址（优先级最高）
    if request:  # 确保request对象存在
        server_ip = get_server_ip_from_request()
        api_url = f"http://{server_ip}:{DEFAULT_CLASH_PORT}"
        logger.info(f"自动生成的Clash API地址: {api_url}")
        return api_url, "自动检测"
    
    # 其次尝试从环境变量获取API地址（优先级次之）
    env_api_url = os.environ.get('YACD_DEFAULT_BACKEND')
    if env_api_url and env_api_url != "auto":
        return env_api_url, "环境变量"
    
    # 如果无法获取IP，则使用默认值
    return f"http://127.0.0.1:{DEFAULT_CLASH_PORT}", "默认值"

def get_original_request_url():
    """获取原始请求的URL，包括协议和主机名部分"""
    forwarded_proto = request.headers.get('X-Forwarded-Proto')
    forwarded_host = request.headers.get('X-Forwarded-Host')
    
    scheme = forwarded_proto or request.scheme
    host = forwarded_host or request.host
    
    return f"{scheme}://{host}"

def hot_reload_clash_config(config_path=None):
    """向Clash API发送热加载配置的请求"""
    try:
        # 如果没有提供配置路径，则使用默认路径
        if config_path is None:
            config_path = CONFIG_FILE
            
        # 获取API基础URL
        api_base_url, source = get_clash_api_url()
        if api_base_url.endswith('/'):
            api_base_url = api_base_url[:-1]
            
        logger.info(f"使用Clash API地址: {api_base_url} (来源: {source})")
        
        # 构建热加载API的URL
        reload_url = f"{api_base_url}/configs"
        
        # 准备请求头
        headers = {"Content-Type": "application/json"}
            
        # 发送PUT请求更新配置
        try:
            # 设置较短的超时时间
            response = requests.put(
                reload_url,
                json={"path": config_path},
                headers=headers,
                timeout=5  # 5秒超时
            )
            
            # 检查响应状态码（204 No Content 表示成功，不返回内容）
            if response.status_code == 204:
                logger.info("Clash配置热加载成功")
                return True, f"配置热加载成功 (API: {api_base_url})", source
            else:
                # 其他状态码表示错误
                error_msg = f"Clash配置热加载失败: HTTP {response.status_code}"
                if response.text:
                    error_msg += f", {response.text}"
                logger.error(error_msg)
                return False, error_msg, source
                
        except requests.exceptions.ConnectionError as e:
            # 连接错误，Clash可能未运行或端口错误
            error_msg = f"无法连接到Clash API: {api_base_url}, 请确认Clash正在运行且端口正确"
            logger.error(f"{error_msg}. 详细错误: {str(e)}")
            return False, error_msg, source
            
        except requests.exceptions.Timeout:
            # 请求超时
            error_msg = f"连接到Clash API超时: {api_base_url}"
            logger.error(error_msg)
            return False, error_msg, source
            
        except requests.exceptions.RequestException as e:
            # 其他请求错误
            error_msg = f"Clash配置热加载请求错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, source
            
    except Exception as e:
        error_msg = f"Clash配置热加载处理异常: {str(e)}"
        logger.error(error_msg)
        return False, error_msg, "异常"

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

@app.route('/get_api_url')
def get_api_url():
    """获取当前使用的Clash API URL"""
    try:
        api_url, source = get_clash_api_url()
        
        # 获取原始请求URL，用于页面展示
        request_origin = get_original_request_url()
        base_path = urllib.parse.urlparse(request_origin).path
        if base_path.endswith('/get_api_url'):
            base_path = base_path[:-12]  # 移除"/get_api_url"
        elif not base_path.endswith('/'):
            base_path += '/'
        
        # 构建YACD界面URL
        yacd_url = f"{request_origin}{base_path}"
        
        return jsonify({
            "api_url": api_url,
            "api_source": source,
            "yacd_url": yacd_url
        })
    except Exception as e:
        logger.error(f"获取API URL失败: {str(e)}")
        return jsonify({
            "api_url": f"http://127.0.0.1:{DEFAULT_CLASH_PORT}",
            "api_source": "错误回退",
            "error": str(e)
        }), 500

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
        
        showStatus(None, "正在保存订阅地址...")
        # 先保存订阅地址，确保地址不会丢失
        # 这里保存原始地址，不添加flag=clash
        save_subscribe_url_to_config(subscribe_url)
        
        showStatus(None, "正在从服务器下载配置...")
        # 为下载添加flag=clash
        download_url = add_clash_flag_to_url(subscribe_url)
        logger.info(f"下载用的订阅URL: {download_url}")
        
        # 下载配置文件
        logger.info("正在下载配置文件...")
        try:
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()  # 检查HTTP错误
        except requests.exceptions.ConnectionError:
            error_msg = "无法连接到订阅服务器，请检查网络连接和订阅地址是否正确"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        except requests.exceptions.Timeout:
            error_msg = "连接订阅服务器超时，请稍后重试"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        except requests.exceptions.HTTPError as e:
            error_msg = f"下载配置失败，服务器返回错误: {response.status_code} {response.reason}"
            logger.error(f"{error_msg}, 详细: {str(e)}")
            return jsonify({"status": "error", "message": error_msg}), 500
        except requests.exceptions.RequestException as e:
            error_msg = f"下载订阅配置失败: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        
        showStatus(None, "正在保存配置文件...")
        # 获取配置内容
        try:
            try:
                config_content = response.content.decode('utf-8')
            except UnicodeDecodeError:
                error_msg = "配置文件内容解码失败，不是有效的文本文件"
                logger.error(error_msg)
                return jsonify({"status": "error", "message": error_msg}), 500
            
            # 检查是否为有效的配置文件 (简单验证)
            if not config_content or len(config_content.strip()) < 10:
                error_msg = "下载的配置文件内容为空或过短，可能不是有效的配置"
                logger.error(error_msg)
                return jsonify({"status": "error", "message": error_msg}), 500
                
            if not any(keyword in config_content for keyword in ['proxies:', 'proxy-groups:', 'rules:']):
                error_msg = "下载的内容不像是有效的Clash配置文件，请检查订阅地址"
                logger.error(error_msg)
                return jsonify({"status": "error", "message": error_msg}), 500
            
            # 保存配置文件前先应用订阅地址
            # 使用原始地址，而不是带flag=clash的
            config_with_url = f"# SUBSCRIBE_URL: {subscribe_url}\n" + config_content
            
            # 直接写入带有订阅地址的配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(config_with_url)
                
            logger.info(f"配置文件(含订阅地址)已保存到: {CONFIG_FILE}")
        except Exception as e:
            error_msg = f"保存配置文件失败: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        
        showStatus(None, "正在修改配置文件...")
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
                error_msg = "配置文件保存后不存在或为空"
                logger.error(error_msg)
                return jsonify({"status": "error", "message": error_msg}), 500
        except Exception as e:
            error_msg = f"修改配置文件失败: {str(e)}"
            logger.error(error_msg)
            return jsonify({"status": "error", "message": error_msg}), 500
        
        showStatus(None, "正在热加载配置...")
        # 执行Clash配置热加载
        success, message, source = hot_reload_clash_config()
        
        if not success:
            logger.warning(f"Clash配置热加载失败：{message}，但配置文件已更新")
            # 即使热加载失败，依然返回成功，因为配置文件已经成功更新
            return jsonify({
                "status": "warning", 
                "message": f"配置文件已成功更新，但热加载失败。您可能需要手动重启Clash或检查Clash是否正在运行。",
                "api_source": source,
                "detail": message
            })
            
        logger.info("订阅配置更新成功")
        return jsonify({
            "status": "success", 
            "message": "订阅配置更新并热加载成功", 
            "api_source": source
        })
    
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
    api_url, _ = get_clash_api_url()
    
    return jsonify({
        "status": "ok", 
        "message": "服务正常运行",
        "config_file": CONFIG_FILE,
        "config_exists": config_exists,
        "config_size": config_size,
        "subscribe_info": {
            "subscribe_url": subscribe_url
        },
        "api_url": api_url
    })

@app.route('/reload_config', methods=['POST'])
def reload_config_endpoint():
    """手动触发Clash配置热加载的API端点"""
    try:
        # 获取可能的配置文件路径
        request_data = request.json or {}
        config_path = request_data.get("config_path", CONFIG_FILE)
            
        success, message, source = hot_reload_clash_config(config_path)
        
        if success:
            return jsonify({
                "status": "success", 
                "message": message,
                "api_source": source
            })
        else:
            return jsonify({
                "status": "error", 
                "message": message,
                "api_source": source
            }), 500
            
    except Exception as e:
        error_msg = f"处理热加载请求时发生错误: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error", 
            "message": error_msg,
            "api_source": "异常"
        }), 500

# 当前任务状态
current_status = {"status": None, "message": ""}

def showStatus(success, message):
    """更新当前任务状态"""
    global current_status
    current_status = {"status": success, "message": message}
    logger.info(f"任务状态: {success}, {message}")

@app.route('/task_status')
def get_task_status():
    """获取当前任务状态"""
    return jsonify(current_status)

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
import * as React from 'react';
import { useTranslation } from 'react-i18next';
import ContentHeader from '~/components/ContentHeader';
import useRemainingViewPortHeight from '~/hooks/useRemainingViewPortHeight';
import { connect } from '~/components/StateProvider';
import { State } from '~/store/types';

// 定义接口以解决类型问题
interface FetchOptions {
  method?: string;
  body?: FormData;
  headers?: Record<string, string>;
}

// 订阅信息接口
interface SubscribeInfo {
  subscribe_url: string;
}

function Subscribe() {
  const [refContainer, containerHeight] = useRemainingViewPortHeight();
  const { t } = useTranslation();
  const [subscribeUrl, setSubscribeUrl] = React.useState('');
  const [configContent, setConfigContent] = React.useState('加载配置中...');
  const [status, setStatus] = React.useState<{
    visible: boolean;
    type: 'success' | 'error' | 'warning';
    title: string;
    message: string;
  }>({
    visible: false,
    type: 'success',
    title: '',
    message: ''
  });
  const [isLoading, setIsLoading] = React.useState(false);
  const [debugInfo, setDebugInfo] = React.useState<string | null>(null);

  // 处理订阅地址，移除flag=clash后缀
  const cleanSubscribeUrl = (url: string): string => {
    if (!url) return '';
    // 移除&flag=clash或?flag=clash
    return url.replace(/[&?]flag=clash$/, '');
  };

  // 尝试不同的请求方式来解决通信问题
  const fetchWithFallback = React.useCallback(async (url: string, options: FetchOptions = {}) => {
    const fullUrl = url.startsWith('http') ? url : window.location.origin + url;
    
    try {
      // 添加调试信息
      console.log(`尝试请求: ${url}, 完整URL: ${fullUrl}`);
      
      // 第一种方式：直接请求
      const response = await fetch(url, options);
      if (response.ok) {
        console.log(`直接请求成功: ${url}`);
        return response;
      }
      
      console.log(`直接请求失败，尝试完整URL: ${fullUrl}`);
      // 如果失败，尝试使用绝对路径
      const absResponse = await fetch(fullUrl, options);
      if (absResponse.ok) {
        console.log(`完整URL请求成功: ${fullUrl}`);
        return absResponse;
      }
      
      throw new Error('所有请求方式都失败');
    } catch (error) {
      console.error('请求失败:', error, '尝试使用XMLHttpRequest');
      
      // 如果fetch都失败，尝试使用XMLHttpRequest
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(options.method || 'GET', url);
        
        if (options.headers) {
          Object.entries(options.headers).forEach(([key, value]) => {
            xhr.setRequestHeader(key, value);
          });
        }
        
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            console.log(`XHR请求成功: ${url}`);
            resolve({
              ok: true,
              status: xhr.status,
              text: () => Promise.resolve(xhr.responseText),
              json: () => Promise.resolve(JSON.parse(xhr.responseText))
            });
          } else {
            reject(new Error(`XHR请求失败: ${xhr.status}`));
          }
        };
        
        xhr.onerror = () => reject(new Error('XHR网络错误'));
        
        if (options.body instanceof FormData) {
          xhr.send(options.body);
        } else {
          xhr.send();
        }
      });
    }
  }, []);

  // 获取保存的订阅信息
  const fetchSubscribeInfo = React.useCallback(async () => {
    try {
      console.log('获取保存的订阅信息...');
      const response = await fetchWithFallback('/sub/get_subscribe_info');
      const data = await response.json() as SubscribeInfo;
      console.log('获取到订阅信息:', data);
      
      if (data && data.subscribe_url) {
        // 清理订阅URL，移除flag=clash
        const cleanedUrl = cleanSubscribeUrl(data.subscribe_url);
        console.log('处理后的订阅地址:', cleanedUrl);
        setSubscribeUrl(cleanedUrl);
        console.log('已设置保存的订阅地址');
        return { ...data, subscribe_url: cleanedUrl };
      }
      
      return data;
    } catch (error) {
      console.error('获取订阅信息失败:', error);
      return { subscribe_url: '' };
    }
  }, [fetchWithFallback]);

  // 检查服务器健康状态
  const checkHealth = React.useCallback(async () => {
    try {
      const response = await fetchWithFallback('/sub/health');
      const data = await response.json();
      setDebugInfo(JSON.stringify(data, null, 2));
      
      // 如果健康检查中包含订阅信息，也设置一下
      if (data && data.subscribe_info && data.subscribe_info.subscribe_url) {
        // 只有当前为空且健康检查有信息时才更新
        if (!subscribeUrl) {
          const cleanedUrl = cleanSubscribeUrl(data.subscribe_info.subscribe_url);
          console.log('从健康检查获取到订阅地址:', cleanedUrl);
          setSubscribeUrl(cleanedUrl);
        }
      }
      
      return data;
    } catch (error) {
      console.error('健康检查失败:', error);
      setDebugInfo(`健康检查失败: ${error instanceof Error ? error.message : '未知错误'}`);
      return null;
    }
  }, [fetchWithFallback, subscribeUrl]);

  // 直接获取配置文件内容的函数
  const fetchConfig = React.useCallback(async () => {
    try {
      console.log('直接请求配置文件...');
      const response = await fetchWithFallback('/sub/get_config');
      return await response.text();
    } catch (error) {
      console.error('直接获取配置失败:', error);
      throw error;
    }
  }, [fetchWithFallback]);

  const loadConfig = React.useCallback(async () => {
    try {
      // 先进行健康检查
      const health = await checkHealth();
      console.log('健康检查结果:', health);
      
      if (health && health.config_exists && health.config_size > 0) {
        console.log('配置文件存在，直接获取配置内容');
        const configText = await fetchConfig();
        setConfigContent(configText);
      } else {
        console.log('配置文件不存在或为空');
        setConfigContent('当前没有可用配置 - 请更新订阅');
      }
    } catch (error) {
      console.error('配置加载错误:', error);
      setConfigContent('获取配置失败 - 请检查连接');
    }
  }, [checkHealth, fetchConfig]);

  // 初始化时加载订阅信息和配置
  React.useEffect(() => {
    // 先获取保存的订阅地址
    fetchSubscribeInfo().then(() => {
      // 然后加载配置
      loadConfig();
    });
    
    // 定期检查健康状态
    const intervalId = setInterval(checkHealth, 15000);
    return () => clearInterval(intervalId);
  }, [fetchSubscribeInfo, loadConfig, checkHealth]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!subscribeUrl) {
      setStatus({
        visible: true,
        type: 'error',
        title: '错误',
        message: '请输入订阅地址'
      });
      return;
    }
    
    setIsLoading(true);
    
    try {
      console.log('准备提交表单...');
      const formData = new FormData();
      formData.append('subscribe_url', subscribeUrl);
      
      console.log('发送请求到:', '/sub/update_config');
      const response = await fetchWithFallback('/sub/update_config', {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      
      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        console.error('解析响应JSON失败:', jsonError);
        // 如果JSON解析失败，尝试获取文本
        const text = await response.text();
        console.log('响应文本:', text);
        throw new Error('服务器响应格式错误');
      }
      
      console.log('收到响应:', data);
      
      setStatus({
        visible: true,
        type: data.status === 'success' ? 'success' : data.status === 'warning' ? 'warning' : 'error',
        title: data.status === 'success' ? '成功' : data.status === 'warning' ? '警告' : '错误',
        message: data.message
      });
      
      if (data.status === 'success') {
        // 成功后重新加载配置
        console.log('提交成功，准备重新加载配置');
        setTimeout(loadConfig, 1000);
      }
    } catch (error) {
      console.error('提交错误:', error);
      setStatus({
        visible: true,
        type: 'error',
        title: '错误',
        message: `请求失败: ${error instanceof Error ? error.message : '未知错误'}`
      });
    } finally {
      setIsLoading(false);
    }
  };

  const containerStyle = {
    height: `${containerHeight}px`,
    overflow: 'auto',
    padding: '20px',
  };

  const cardStyle = {
    background: 'white',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
    marginBottom: '20px',
    overflow: 'hidden',
  };

  const cardBodyStyle = {
    padding: '20px',
  };

  const formGroupStyle = {
    marginBottom: '20px',
  };

  const labelStyle = {
    display: 'block',
    marginBottom: '8px',
    fontWeight: 'bold',
    color: '#2c3e50',
  };

  const inputStyle = {
    width: '100%',
    padding: '12px 15px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '16px',
  };

  const buttonStyle = {
    padding: '12px 24px',
    background: '#3498db',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    cursor: 'pointer',
  };

  const statusCardStyle = {
    ...cardStyle,
    borderLeft: `4px solid ${
      status.type === 'success' 
        ? '#2ecc71' 
        : status.type === 'warning' 
          ? '#f39c12' 
          : '#e74c3c'
    }`,
    display: status.visible ? 'block' : 'none',
  };

  const configContainerStyle = {
    border: '1px solid #ddd',
    borderRadius: '4px',
    padding: '10px',
    backgroundColor: '#f8f9fa',
    maxHeight: '300px',
    overflow: 'auto',
  };

  const preStyle = {
    margin: 0,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  };

  const debugStyle = {
    marginTop: '20px',
    padding: '10px',
    backgroundColor: '#f8f9fa',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '12px',
    display: debugInfo ? 'block' : 'none',
  };

  return (
    <div>
      <ContentHeader title={t('订阅')} />
      <div ref={refContainer} style={containerStyle}>
        <div style={cardStyle}>
          <div style={cardBodyStyle}>
            <form onSubmit={handleSubmit}>
              <div style={formGroupStyle}>
                <label style={labelStyle} htmlFor="subscribe_url">{t('订阅地址 (SUBSCRIBE_URL)')}</label>
                <input
                  id="subscribe_url"
                  type="text"
                  value={subscribeUrl}
                  onChange={(e) => setSubscribeUrl(e.target.value)}
                  placeholder={t('请输入您的订阅地址')}
                  required
                  style={inputStyle}
                />
              </div>
              <div style={{ textAlign: 'center' }}>
                <button
                  type="submit"
                  style={buttonStyle}
                  disabled={isLoading}
                >
                  {isLoading ? t('更新中...') : t('更新配置')}
                </button>
              </div>
            </form>
          </div>
        </div>
        
        <div style={statusCardStyle}>
          <div style={cardBodyStyle}>
            <h3>{t(status.title)}</h3>
            <p>{t(status.message)}</p>
          </div>
        </div>
        
        <div>
          <h3 style={{ marginBottom: '10px' }}>{t('当前配置文件内容')}</h3>
          <div style={configContainerStyle}>
            <pre style={preStyle}>{configContent}</pre>
          </div>
        </div>
        
        <div style={debugStyle}>
          <h4>服务器状态:</h4>
          <pre>{debugInfo}</pre>
        </div>
      </div>
    </div>
  );
}

const mapState = (s: State) => ({});

export default connect(mapState)(Subscribe);

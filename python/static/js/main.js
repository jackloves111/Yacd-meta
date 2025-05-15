// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 加载当前配置
    loadConfig();
    
    // 加载API URL
    loadApiUrl();
    
    const subscribeInput = document.getElementById('subscribe_url');
    const resetUrlBtn = document.getElementById('resetUrlBtn');
    
    // 获取保存的订阅URL并填充输入框
    fetch('/get_subscribe_info')
        .then(response => response.json())
        .then(data => {
            if (subscribeInput && data.subscribe_url) {
                // 填充输入框
                subscribeInput.value = data.subscribe_url;
                
                // 保存原始值以便重置
                subscribeInput.dataset.originalValue = data.subscribe_url;
                
                // 显示重置按钮
                if (resetUrlBtn) {
                    resetUrlBtn.style.display = 'inline-block';
                }
            } else {
                // 没有保存的订阅地址，隐藏重置按钮
                if (resetUrlBtn) {
                    resetUrlBtn.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('获取订阅信息失败:', error);
            // 出错时隐藏重置按钮
            if (resetUrlBtn) {
                resetUrlBtn.style.display = 'none';
            }
        });
    
    // 监听重置按钮点击事件
    if (resetUrlBtn) {
        resetUrlBtn.addEventListener('click', function() {
            if (subscribeInput && subscribeInput.dataset.originalValue) {
                subscribeInput.value = subscribeInput.dataset.originalValue;
                subscribeInput.focus();
                subscribeInput.select(); // 选中文本
            }
        });
    }
    
    // 给订阅地址输入框添加焦点事件，点击时选中全部文本
    if (subscribeInput) {
        subscribeInput.addEventListener('focus', function() {
            this.select();
        });
    }
    
    // 监听表单提交事件
    document.getElementById('updateForm').addEventListener('submit', function(e) {
        e.preventDefault();
        updateConfig();
    });
    
    // 监听热加载按钮
    document.getElementById('reloadConfigBtn').addEventListener('click', function() {
        reloadConfig();
    });
});

// 更新配置
function updateConfig() {
    const subscribeUrl = document.getElementById('subscribe_url').value.trim();
    if (!subscribeUrl) {
        showStatus(false, "订阅地址不能为空");
        return;
    }
    
    // 重置并显示进度条
    resetProgress();
    document.getElementById('progressContainer').classList.remove('hidden');
    
    // 禁用按钮
    const updateBtn = document.getElementById('updateBtn');
    updateBtn.disabled = true;
    updateBtn.innerText = '更新中...';
    
    // 开始进度动画
    setProgress(10);
    updateStepStatus('save', 'active');
    
    // 启动状态轮询
    startStatusPolling();
    
    const formData = new FormData();
    formData.append('subscribe_url', subscribeUrl);
    
    fetch('/update_config', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // 停止状态轮询
        stopStatusPolling();
        
        // 完成进度
        setProgress(100);
        
        // 显示结果
        if (data.status === 'success') {
            showStatus(true, data.message, data.api_source);
            // 更新成功后重新加载配置
            loadConfig();
            // 更新API URL信息
            loadApiUrl();
        } else if (data.status === 'warning') {
            // 对于警告状态，显示详细错误信息
            showWarningStatus(data.message, data.api_source, data.detail);
        } else {
            showStatus(false, data.message || "更新失败", data.api_source);
        }
    })
    .catch(error => {
        // 停止状态轮询
        stopStatusPolling();
        
        console.error('更新配置失败:', error);
        showStatus(false, "更新配置失败: " + error.message);
        // 重置进度条
        setProgress(0);
    })
    .finally(() => {
        // 恢复按钮状态
        updateBtn.disabled = false;
        updateBtn.innerText = '更新配置';
    });
}

// 状态轮询计时器
let statusPollingTimer = null;

// 开始状态轮询
function startStatusPolling() {
    // 每500毫秒查询一次状态
    statusPollingTimer = setInterval(pollTaskStatus, 500);
}

// 停止状态轮询
function stopStatusPolling() {
    if (statusPollingTimer) {
        clearInterval(statusPollingTimer);
        statusPollingTimer = null;
    }
}

// 轮询任务状态
function pollTaskStatus() {
    fetch('/task_status')
        .then(response => response.json())
        .then(data => {
            if (data.status === null) return; // 无状态更新
            
            const message = data.message;
            
            // 根据消息更新进度和步骤状态
            if (message.includes("保存订阅地址")) {
                updateStepStatus('save', 'completed');
                updateStepStatus('download', 'active');
                setProgress(25);
            } else if (message.includes("下载配置")) {
                updateStepStatus('download', 'completed');
                updateStepStatus('modify', 'active');
                setProgress(50);
            } else if (message.includes("修改配置文件")) {
                updateStepStatus('modify', 'completed');
                updateStepStatus('reload', 'active');
                setProgress(75);
            } else if (message.includes("热加载配置")) {
                setProgress(90);
            }
        })
        .catch(error => {
            console.error('轮询任务状态失败:', error);
        });
}

// 重置进度显示
function resetProgress() {
    setProgress(0);
    document.querySelectorAll('.step').forEach(step => {
        step.className = 'step';
        step.querySelector('.step-status').textContent = '';
    });
}

// 设置进度条百分比
function setProgress(percent) {
    document.getElementById('progressBar').style.width = percent + '%';
}

// 更新步骤状态
function updateStepStatus(stepId, status, message = '') {
    const step = document.querySelector(`.step[data-step="${stepId}"]`);
    if (!step) return;
    
    // 移除所有状态类
    step.classList.remove('active', 'completed', 'error');
    
    // 添加新状态类
    if (status) {
        step.classList.add(status);
    }
    
    // 更新状态消息
    if (message) {
        step.querySelector('.step-status').textContent = message;
    }
}

// 加载API URL
function loadApiUrl() {
    const currentApiUrl = document.getElementById('currentApiUrl');
    const currentApiSource = document.getElementById('currentApiSource');
    const yacdUrl = document.getElementById('yacdUrl');
    currentApiUrl.textContent = "检测中...";
    currentApiSource.textContent = "检测中...";
    yacdUrl.textContent = "检测中...";
    
    fetch('/get_api_url')
        .then(response => response.json())
        .then(data => {
            currentApiUrl.textContent = data.api_url || "自动检测失败";
            currentApiSource.textContent = data.api_source || "未知";
            
            // 显示YACD面板地址
            if (data.yacd_url) {
                const link = document.createElement('a');
                link.href = data.yacd_url;
                link.textContent = data.yacd_url;
                link.target = '_blank';
                yacdUrl.innerHTML = '';
                yacdUrl.appendChild(link);
            } else {
                yacdUrl.textContent = "无法获取";
            }
        })
        .catch(error => {
            console.error('加载API URL失败:', error);
            currentApiUrl.textContent = "检测失败";
            currentApiSource.textContent = "检测失败";
            yacdUrl.textContent = "检测失败";
        });
}

// 手动热加载配置
function reloadConfig() {
    // 显示处理中状态
    showStatus(null, "正在热加载配置...");
    
    // 禁用按钮防止重复点击
    const reloadBtn = document.getElementById('reloadConfigBtn');
    reloadBtn.disabled = true;
    reloadBtn.innerHTML = '<i class="icon-refresh icon-spin"></i> 热加载中...';
    
    fetch('/reload_config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showStatus(true, data.message, data.api_source);
        } else {
            // 如果热加载失败，显示错误信息
            showStatus(false, data.message || "热加载失败", data.api_source);
        }
    })
    .catch(error => {
        console.error('热加载配置失败:', error);
        showStatus(false, "热加载配置失败: " + error.message);
    })
    .finally(() => {
        // 恢复按钮状态
        reloadBtn.disabled = false;
        reloadBtn.innerHTML = '<i class="icon-refresh"></i> 热加载配置';
    });
}

// 加载当前配置
function loadConfig() {
    const configContent = document.getElementById('configContent');
    configContent.textContent = "正在加载配置...";
    
    fetch('/get_config')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(data => {
            configContent.textContent = data;
        })
        .catch(error => {
            console.error('加载配置失败:', error);
            configContent.textContent = "加载配置失败: " + error.message;
        });
}

// 显示状态消息
function showStatus(success, message, apiSource = null) {
    const statusCard = document.getElementById('statusCard');
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const apiSourceInfo = document.getElementById('apiSourceInfo');
    const apiSourceSpan = document.getElementById('apiSource');
    
    statusCard.classList.remove('hidden');
    
    if (success === null) {
        // 处理中
        statusCard.className = 'card status-card status-processing';
        statusTitle.textContent = "处理中";
        apiSourceInfo.classList.add('hidden');
    } else if (success) {
        // 成功
        statusCard.className = 'card status-card status-success';
        statusTitle.textContent = "操作成功";
        // 完成最后一个步骤
        updateStepStatus('reload', 'completed');
    } else {
        // 失败
        statusCard.className = 'card status-card status-error';
        statusTitle.textContent = "操作失败";
        // 标记当前进行中的步骤为错误
        document.querySelector('.step.active')?.classList.add('error');
    }
    
    statusMessage.textContent = message;
    
    // 显示API来源信息
    if (apiSource) {
        apiSourceSpan.textContent = apiSource;
        apiSourceInfo.classList.remove('hidden');
    } else {
        apiSourceInfo.classList.add('hidden');
    }
}

// 显示警告状态
function showWarningStatus(message, apiSource = null, detail = null) {
    const statusCard = document.getElementById('statusCard');
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const apiSourceInfo = document.getElementById('apiSourceInfo');
    const apiSourceSpan = document.getElementById('apiSource');
    
    statusCard.classList.remove('hidden');
    statusCard.className = 'card status-card status-warning';
    statusTitle.textContent = "部分成功";
    
    // 处理消息显示，可能包含详细信息
    if (detail) {
        const messageElement = document.createElement('div');
        
        // 添加主要消息
        const mainMessage = document.createElement('p');
        mainMessage.textContent = message;
        messageElement.appendChild(mainMessage);
        
        // 添加"查看详情"按钮
        const detailsContainer = document.createElement('div');
        detailsContainer.className = 'details-container';
        
        const detailsButton = document.createElement('button');
        detailsButton.className = 'details-toggle';
        detailsButton.textContent = '查看错误详情';
        detailsButton.onclick = function() {
            const detailsContent = this.nextElementSibling;
            if (detailsContent.style.display === 'none' || !detailsContent.style.display) {
                detailsContent.style.display = 'block';
                this.textContent = '隐藏错误详情';
            } else {
                detailsContent.style.display = 'none';
                this.textContent = '查看错误详情';
            }
        };
        
        const detailsContent = document.createElement('div');
        detailsContent.className = 'details-content';
        detailsContent.style.display = 'none';
        
        const detailText = document.createElement('p');
        detailText.className = 'error-detail';
        detailText.textContent = detail;
        
        detailsContent.appendChild(detailText);
        detailsContainer.appendChild(detailsButton);
        detailsContainer.appendChild(detailsContent);
        
        messageElement.appendChild(detailsContainer);
        
        // 替换现有的消息元素内容
        statusMessage.innerHTML = '';
        statusMessage.appendChild(messageElement);
    } else {
        statusMessage.textContent = message;
    }
    
    // 标记热加载步骤为错误
    updateStepStatus('reload', 'error', '失败');
    
    // 显示API来源信息
    if (apiSource) {
        apiSourceSpan.textContent = apiSource;
        apiSourceInfo.classList.remove('hidden');
    } else {
        apiSourceInfo.classList.add('hidden');
    }
}
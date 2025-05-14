document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('updateForm');
    const statusCard = document.getElementById('statusCard');
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const updateBtn = document.getElementById('updateBtn');
    
    // 获取当前路径
    const currentPath = window.location.pathname;
    const basePath = currentPath.endsWith('/') ? currentPath : currentPath + '/';
    
    // 表单提交事件
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 获取表单数据
        const subscribeUrl = document.getElementById('subscribe_url').value;
        
        if (!subscribeUrl) {
            showStatus('error', '错误', '请输入订阅地址');
            return;
        }
        
        // 禁用按钮并显示加载状态
        updateBtn.disabled = true;
        updateBtn.textContent = '更新中...';
        
        // 准备表单数据
        const formData = new FormData();
        formData.append('subscribe_url', subscribeUrl);
        
        // 发送请求
        fetch('update_config', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showStatus('success', '成功', data.message);
            } else if (data.status === 'warning') {
                showStatus('warning', '警告', data.message);
            } else {
                showStatus('error', '错误', data.message);
            }
        })
        .catch(error => {
            showStatus('error', '错误', '请求失败: ' + error.message);
        })
        .finally(() => {
            // 恢复按钮状态
            updateBtn.disabled = false;
            updateBtn.textContent = '更新配置';
        });
    });
    
    // 显示状态信息
    function showStatus(type, title, message) {
        statusCard.className = 'card status-card ' + type;
        statusTitle.textContent = title;
        statusMessage.textContent = message;
        statusCard.classList.remove('hidden');
        
        // 滚动到状态卡片
        statusCard.scrollIntoView({ behavior: 'smooth' });
    }
});

// 新增配置加载功能
function loadConfig() {
    fetch('/get_config')
        .then(response => {
            if (!response.ok) throw new Error('配置加载失败');
            return response.text();
        })
        .then(text => {
            document.getElementById('configContent').textContent = text;
        })
        .catch(error => {
            document.getElementById('configContent').textContent = error.message;
        });
}

// 页面加载时自动获取配置
document.addEventListener('DOMContentLoaded', loadConfig);
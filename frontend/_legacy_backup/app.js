// InkAI 小说创作系统前端应用

// InkAI 前端应用已加载
console.log('InkAI 前端应用开始加载...');
console.log('JavaScript语法检查通过');

// 全局状态管理
const AppState = {
    currentPage: 'welcome',
    currentNovelId: null,
    selectedNovelId: null,
    workflowData: null,
    continuationData: null
};

console.log('AppState 初始化完成:', AppState);

// API 基础URL
const API_BASE = '/api';

// 工具函数
const Utils = {
    // 生成质量评估HTML
    generateQualityAssessmentHTML: (qualityAssessment, showTitle = true) => {
        if (!qualityAssessment) return '';
        
        const titleHTML = showTitle ? '<h6><i class="fas fa-star me-2"></i>质量评估</h6>' : '';
        const scoreClass = qualityAssessment.overall_score >= 80 ? 'high' : qualityAssessment.overall_score >= 60 ? 'medium' : 'low';
        
        return `
            ${titleHTML}
            <div class="quality-assessment mb-3">
                <div class="quality-score ${scoreClass}">
                    <i class="fas fa-star me-2"></i>
                    质量评分: ${qualityAssessment.overall_score}分
                </div>
                ${qualityAssessment.suggestions && qualityAssessment.suggestions.length > 0 ? `
                    <div class="quality-suggestions mt-2">
                        <h6 class="text-warning">改进建议:</h6>
                        <ul class="suggestions-list">
                            ${qualityAssessment.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    },
    // 格式化章节内容
    formatChapterContent: (content) => {
        if (!content) return '';
        // 先处理转义的换行符，再转换为HTML换行
        return content.replace(/\\n/g, '\n').replace(/\n/g, '<br>');
    },
    // 通用API调用方法
    callNovelAPI: async (novelId, endpoint, method = 'GET', data = null) => {
        const options = { method };
        if (data) {
            options.body = JSON.stringify(data);
        }
        return await Utils.apiRequest(`/novels/${novelId}${endpoint}`, options);
    },
    // 显示加载状态
    showLoading: (message = '正在处理中，请稍候...') => {
        const overlay = document.getElementById('loading-overlay');
        const content = overlay.querySelector('.loading-content p');
        content.textContent = message;
        overlay.style.display = 'flex';
    },

    // 隐藏加载状态
    hideLoading: () => {
        document.getElementById('loading-overlay').style.display = 'none';
    },

    // 显示消息提示
    showMessage: (message, type = 'info', duration = 5000) => {
        const container = document.getElementById('message-container');
        const alertId = 'alert-' + Date.now();
        
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', alertHtml);
        
        // 自动移除
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                alert.remove();
            }
        }, duration);
    },

    // API 请求封装
    apiRequest: async (url, options = {}) => {
        try {
            // 添加时间戳防止缓存
            const separator = url.includes('?') ? '&' : '?';
            const timestampedUrl = url + separator + '_t=' + Date.now();
            
            const response = await fetch(API_BASE + timestampedUrl, {
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache',
                    ...options.headers
                },
                ...options
            });
            
            // 检查响应状态
            if (!response.ok) {
                let errorMessage = '请求失败';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // 如果响应不是JSON格式，使用状态文本
                    errorMessage = response.statusText || errorMessage;
                }
                throw new Error(`${response.status}: ${errorMessage}`);
            }
            
            const data = await response.json();
            
            // 检查业务逻辑错误
            if (data && data.success === false) {
                throw new Error(data.error || '操作失败');
            }
            
            return data;
        } catch (error) {
            console.error('API请求错误:', error);
            
            // 网络错误处理
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('网络连接失败，请检查网络设置');
            }
            
            // 超时错误处理
            if (error.name === 'AbortError') {
                throw new Error('请求超时，请稍后重试');
            }
            
            throw error;
        }
    },

    // 格式化日期
    formatDate: (dateString) => {
        if (!dateString) return '未知时间';
        
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return '时间格式错误';
        }
        
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // 格式化字数
    formatWordCount: (count) => {
        if (count >= 10000) {
            return (count / 10000).toFixed(1) + '万';
        }
        return count.toString();
    }
};

// 页面切换函数
const Navigation = {
    showPage: (pageId) => {
        // 隐藏所有页面
        document.querySelectorAll('.page').forEach(page => {
            page.style.display = 'none';
        });
        
        // 显示目标页面
        const targetPage = document.getElementById(pageId);
        if (targetPage) {
            targetPage.style.display = 'block';
            AppState.currentPage = pageId;
        }
    },

    showWelcome: () => {
        Navigation.showPage('welcome-page');
    },

    showCreateNovel: () => {
        Navigation.showPage('create-novel-page');
    },

    showContinueNovel: () => {
        console.log('showContinueNovel 被调用');
        Navigation.showPage('continue-novel-page');
        console.log('页面已切换到 continue-novel-page');
        NovelManager.loadContinuationNovelList();
        console.log('loadContinuationNovelList 已调用');
    },

    showNovelList: () => {
        Navigation.showPage('novel-list-page');
        NovelManager.loadNovelList();
    },

    showCreationWorkflow: (novelId) => {
        AppState.currentNovelId = novelId;
        Navigation.showPage('creation-workflow-page');
        WorkflowManager.loadCreationWorkflow(novelId);
    },

    showContinuationWorkflow: (novelId) => {
        AppState.currentNovelId = novelId;
        Navigation.showPage('continuation-workflow-page');
        ContinuationManager.loadContinuationWorkflow(novelId);
    },

    // 导航辅助函数
    goToHome: () => {
        Navigation.showWelcome();
    },

    goToNovelList: () => {
        Navigation.showNovelList();
    },

    goToContinuationNovelList: () => {
        Navigation.showContinueNovel();
    },

    showQuickContinuationProgress: (novelId) => {
        AppState.currentNovelId = novelId;
        Navigation.showPage('quick-continuation-progress-page');
        QuickContinuationManager.loadProgress(novelId);
    }
};

// 小说管理功能
const NovelManager = {
    // 创建新小说
    createNovel: async (title, requirements) => {
        try {
            Utils.showLoading('正在创建小说项目...');
            
            const response = await Utils.apiRequest('/novels', {
                method: 'POST',
                body: JSON.stringify({
                    title: title,
                    user_requirements: requirements
                })
            });
            
            if (response.success) {
                Utils.showMessage('小说项目创建成功！', 'success');
                AppState.currentNovelId = response.data.novel_id;
                
                // 自动选择标签
                await NovelManager.selectTags(response.data.novel_id);
            }
        } catch (error) {
            Utils.showMessage('创建小说失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    // 选择标签
    selectTags: async (novelId) => {
        try {
            Utils.showLoading('正在分析需求并推荐标签...');
            
            const response = await Utils.apiRequest(`/novels/${novelId}/tags`, {
                method: 'POST'
            });
            
            if (response.success) {
                Utils.showMessage('标签推荐完成！', 'success');
                Navigation.showCreationWorkflow(novelId);
            }
        } catch (error) {
            Utils.showMessage('标签选择失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    // 加载小说列表
    loadNovelList: async () => {
        try {
            const response = await Utils.apiRequest('/novels');
            
            if (response.success) {
                const novels = response.data;
                displayNovelList(novels);
            }
        } catch (error) {
            Utils.showMessage('加载小说列表失败: ' + error.message, 'danger');
        }
    },

    // 加载续写小说列表
    loadContinuationNovelList: async () => {
        try {
            console.log('开始加载续写小说列表...');
            const response = await Utils.apiRequest('/novels');
            console.log('API响应:', response);
            
            if (response.success) {
                const novels = response.data;
                console.log('小说数据:', novels);
                displayContinuationNovelList(novels);
                console.log('displayContinuationNovelList 已调用');
            } else {
                console.error('API返回失败:', response);
            }
        } catch (error) {
            console.error('加载小说列表失败:', error);
            Utils.showMessage('加载小说列表失败: ' + error.message, 'danger');
        }
    },

    // 开始续写
    startContinuation: async (novelId, requirements) => {
        try {
            // 首先检查是否有现有的续写进度
            const statusResponse = await Utils.apiRequest(`/novels/${novelId}/continuation-status`);
            
            let resetCache = false;
            
            if (statusResponse.success && statusResponse.data.is_continuation) {
                // 有现有进度，询问用户是否继续
                const currentStep = statusResponse.data.current_step;
                const hasProgress = currentStep && currentStep !== 'not_started' && currentStep !== 'storyline_generation';
                
                if (hasProgress) {
                    const userChoice = await showContinuationOptionsDialog(currentStep);
                    if (userChoice === 'cancel') {
                        return; // 用户取消操作
                    }
                    resetCache = (userChoice === 'restart');
                }
            }
            
            Utils.showLoading(resetCache ? '正在重新启动续写流程...' : '正在启动续写流程...');
            
            const response = await Utils.apiRequest(`/novels/${novelId}/continuation`, {
                method: 'POST',
                body: JSON.stringify({
                    user_requirements: requirements,
                    reset_cache: resetCache
                })
            });
            
            if (response.success) {
                const message = response.data.status === 'continued' ? 
                    '续写流程已恢复！' : '续写流程启动成功！';
                Utils.showMessage(message, 'success');
                Navigation.showContinuationWorkflow(novelId);
            }
        } catch (error) {
            Utils.showMessage('启动续写失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 显示续写选项对话框
const showContinuationOptionsDialog = (currentStep) => {
    return new Promise((resolve) => {
        const stepNames = {
            'storyline_improvement': '故事线优化',
            'chapter_writing': '章节写作',
            'content_improvement': '内容优化',
            'chapter_save': '章节保存',
            'quality_assessment': '质量评估',
            'chapter_quality_assessment': '章节质量评估'
        };
        
        const friendlyStepName = stepNames[currentStep] || currentStep;
        
        const modalHtml = `
            <div class="modal fade" id="continuationOptionsModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-question-circle me-2"></i>
                                检测到续写进度
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                检测到您有未完成的续写进度，当前步骤：<strong>${friendlyStepName}</strong>
                            </div>
                            
                            <p class="mb-3">您希望如何处理？</p>
                            
                            <div class="d-grid gap-2">
                                <button type="button" class="btn btn-primary btn-lg" onclick="resolveContinuationDialog('continue')">
                                    <i class="fas fa-play me-2"></i>
                                    继续上次进度
                                    <small class="d-block text-light mt-1">保留已生成的内容，从当前步骤继续</small>
                                </button>
                                
                                <button type="button" class="btn btn-warning btn-lg" onclick="resolveContinuationDialog('restart')">
                                    <i class="fas fa-redo me-2"></i>
                                    重新开始续写
                                    <small class="d-block text-light mt-1">清除所有进度，从头开始生成</small>
                                </button>
                                
                                <button type="button" class="btn btn-secondary" onclick="resolveContinuationDialog('cancel')">
                                    <i class="fas fa-times me-2"></i>
                                    取消操作
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 移除已存在的模态框
        const existingModal = document.getElementById('continuationOptionsModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 添加新的模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 存储resolve函数
        window.continuationDialogResolve = resolve;
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('continuationOptionsModal'));
        modal.show();
    });
};

// 处理续写对话框的选择
window.resolveContinuationDialog = (choice) => {
    const modal = bootstrap.Modal.getInstance(document.getElementById('continuationOptionsModal'));
    modal.hide();
    
    if (window.continuationDialogResolve) {
        window.continuationDialogResolve(choice);
        window.continuationDialogResolve = null;
    }
};

// 工作流程管理
const WorkflowManager = {
    // 加载创作工作流程
    loadCreationWorkflow: async (novelId) => {
        try {
            const response = await Utils.apiRequest(`/novels/${novelId}/workflow-status`);
            
            if (response.success) {
                AppState.workflowData = response.data;
                displayCreationWorkflow(response.data);
            }
        } catch (error) {
            Utils.showMessage('加载工作流程状态失败: ' + error.message, 'danger');
        }
    },

    // 执行工作流程步骤
    executeStep: async (stepName, novelId) => {
        try {
            // 根据步骤类型显示具体的加载提示
            const stepMessages = {
                'character_creation': '正在创建人物形象，AI正在分析角色设定...',
                'storyline_generation': '正在生成故事线，AI正在构思情节发展...',
                'knowledge_graph_creation': '正在创建知识图谱，AI正在整理故事要素...',
                'chapter_writing': '正在写作章节内容，AI正在创作精彩故事...',
                'chapter_completed': '小说创作已完成！'
            };
            
            const loadingMessage = stepMessages[stepName] || `正在执行${stepName}...`;
            Utils.showLoading(loadingMessage);
            
            let response;
            switch (stepName) {
                case 'character_creation':
                    response = await Utils.callNovelAPI(novelId, '/characters', 'POST');
                    break;
                case 'storyline_generation':
                    response = await Utils.callNovelAPI(novelId, '/storyline', 'POST');
                    break;
                case 'knowledge_graph_creation':
                    response = await Utils.callNovelAPI(novelId, '/knowledge-graph', 'POST');
                    break;
                case 'chapter_writing':
                    response = await Utils.callNovelAPI(novelId, '/chapters', 'POST');
                    break;
                case 'chapter_completed':
                    // 创作完成状态，不需要执行任何操作
                    Utils.showMessage('小说创作已完成！', 'success');
                    return;
                default:
                    throw new Error('未知的步骤: ' + stepName);
            }
            
            if (response.success) {
                const successMessages = {
                    'character_creation': '人物形象创建成功！',
                    'storyline_generation': '故事线生成成功！',
                    'knowledge_graph_creation': '知识图谱创建成功！',
                    'chapter_writing': '章节写作完成！'
                };
                Utils.showMessage(successMessages[stepName] || `${stepName}执行成功！`, 'success');
                // 重新加载工作流程状态
                await WorkflowManager.loadCreationWorkflow(novelId);
            }
        } catch (error) {
            Utils.showMessage(`执行${stepName}失败: ` + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    // 改进内容
    improveContent: async (type, novelId, suggestions) => {
        try {
            Utils.showLoading(`正在改进${type}...`);
            
            let response;
            if (type === 'characters') {
                response = await Utils.apiRequest(`/novels/${novelId}/characters/improve`, {
                    method: 'POST',
                    body: JSON.stringify({ suggestions })
                });
            } else if (type === 'storyline') {
                response = await Utils.apiRequest(`/novels/${novelId}/storyline/improve`, {
                    method: 'POST',
                    body: JSON.stringify({ suggestions })
                });
            }
            
            if (response.success) {
                Utils.showMessage(`${type}改进成功！`, 'success');
                await WorkflowManager.loadCreationWorkflow(novelId);
            }
        } catch (error) {
            Utils.showMessage(`改进${type}失败: ` + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 快速续写管理
const QuickContinuationManager = {
    // 加载进度
    loadProgress: async (novelId) => {
        try {
            const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick/progress`);
            if (response.success) {
                AppState.quickContinuationProgress = response.data;
                displayQuickContinuationProgress(response.data);
                
                // 如果任务还在运行，设置定时刷新
                if (response.data.status === 'running') {
                    QuickContinuationManager.startProgressPolling(novelId);
                }
            } else {
                Utils.showMessage('获取快速续写进度失败: ' + response.error, 'danger');
            }
        } catch (error) {
            Utils.showMessage('获取快速续写进度失败: ' + error.message, 'danger');
        }
    },

    // 开始进度轮询
    startProgressPolling: (novelId) => {
        // 清除之前的定时器
        if (AppState.progressPollingTimer) {
            clearInterval(AppState.progressPollingTimer);
        }
        
        // 设置新的定时器，每3秒刷新一次（更频繁的更新）
        let retryCount = 0;
        const maxRetries = 5;
        
        AppState.progressPollingTimer = setInterval(async () => {
            try {
                const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick/progress`);
                if (response.success) {
                    // 重置重试计数
                    retryCount = 0;
                    
                    const previousProgress = AppState.quickContinuationProgress;
                    AppState.quickContinuationProgress = response.data;
                    updateQuickContinuationProgress(response.data);
                    
                    // 检查是否有新章节完成
                    if (previousProgress && response.data.completed_chapters > previousProgress.completed_chapters) {
                        console.log(`检测到第${response.data.completed_chapters}章完成，立即刷新数据...`);
                        
                        // 立即更新章节详情列表
                        updateChapterDetailsList(response.data);
                        
                        // 刷新其他相关数据
                        await refreshNovelDataAfterCompletion(novelId, response.data.completed_chapters);
                    }
                    
                    // 如果任务完成或失败，停止轮询并刷新相关数据
                    if (response.data.status === 'completed' || response.data.status === 'failed') {
                        QuickContinuationManager.stopProgressPolling();
                        
                        // 显示最终结果
                        if (response.data.status === 'completed') {
                            console.log('快速续写任务完成，开始刷新相关数据...');
                            Utils.showMessage('快速续写任务完成！', 'success');
                            await refreshNovelDataAfterCompletion(novelId);
                        } else if (response.data.status === 'failed') {
                            Utils.showMessage(`快速续写任务失败: ${response.data.error_message || '未知错误'}`, 'danger');
                        }
                    }
                } else {
                    console.error('获取进度失败:', response.error);
                    
                    // 如果是任务不存在，停止轮询
                    if (response.error && response.error.includes('未找到')) {
                        QuickContinuationManager.stopProgressPolling();
                        Utils.hideLoading();
                    } else {
                        // 其他错误，增加重试计数
                        retryCount++;
                        if (retryCount >= maxRetries) {
                            console.error('达到最大重试次数，停止轮询');
                            QuickContinuationManager.stopProgressPolling();
                            Utils.hideLoading();
                            Utils.showMessage('获取进度失败，请刷新页面重试', 'warning');
                        }
                    }
                }
            } catch (error) {
                console.error('轮询进度失败:', error);
                
                // 网络错误时，增加重试计数
                if (error.name === 'TypeError' || error.message.includes('fetch')) {
                    retryCount++;
                    console.log(`网络连接中断，重试 ${retryCount}/${maxRetries}`);
                    
                    if (retryCount >= maxRetries) {
                        console.error('达到最大重试次数，停止轮询');
                        QuickContinuationManager.stopProgressPolling();
                        Utils.hideLoading();
                        Utils.showMessage('网络连接中断，请检查网络后刷新页面', 'warning');
                    }
                } else {
                    // 其他错误，直接停止轮询
                    QuickContinuationManager.stopProgressPolling();
                    Utils.hideLoading();
                }
            }
        }, 3000); // 改为3秒轮询，更及时
    },

    // 停止进度轮询
    stopProgressPolling: () => {
        if (AppState.progressPollingTimer) {
            clearInterval(AppState.progressPollingTimer);
            AppState.progressPollingTimer = null;
        }
    },

    // 停止任务
    stopTask: async (novelId) => {
        try {
            Utils.showLoading('正在停止任务...');
            const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick/stop`, {
                method: 'POST'
            });
            
            if (response.success) {
                Utils.showMessage('任务已停止', 'success');
                QuickContinuationManager.loadProgress(novelId);
            } else {
                Utils.showMessage('停止任务失败: ' + response.error, 'danger');
            }
        } catch (error) {
            Utils.showMessage('停止任务失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    // 暂停任务
    pauseTask: async (novelId) => {
        try {
            Utils.showLoading('正在暂停任务...');
            const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick/pause`, {
                method: 'POST'
            });
            
            if (response.success) {
                Utils.showMessage('任务已暂停', 'success');
                QuickContinuationManager.loadProgress(novelId);
            } else {
                Utils.showMessage('暂停任务失败: ' + response.error, 'danger');
            }
        } catch (error) {
            Utils.showMessage('暂停任务失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    },

    // 恢复任务
    resumeTask: async (novelId) => {
        try {
            Utils.showLoading('正在恢复任务...');
            const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick/resume`, {
                method: 'POST'
            });
            
            if (response.success) {
                Utils.showMessage('任务已恢复', 'success');
                QuickContinuationManager.loadProgress(novelId);
                QuickContinuationManager.startProgressPolling(novelId);
            } else {
                Utils.showMessage('恢复任务失败: ' + response.error, 'danger');
            }
        } catch (error) {
            Utils.showMessage('恢复任务失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 续写流程管理
const ContinuationManager = {
    // 加载续写工作流程
    loadContinuationWorkflow: async (novelId) => {
        try {
            const response = await Utils.apiRequest(`/novels/${novelId}/continuation-status`);
            
            if (response.success) {
                AppState.continuationData = response.data;
                displayContinuationWorkflow(response.data);
            }
        } catch (error) {
            Utils.showMessage('加载续写状态失败: ' + error.message, 'danger');
        }
    },

    // 执行续写步骤
    executeContinuationStep: async (stepName, novelId) => {
        try {
            Utils.showLoading(`正在执行${stepName}...`);
            
            let response;
            switch (stepName) {
                case 'storyline_generation':
                    response = await Utils.apiRequest(`/novels/${novelId}/continuation/storyline`, {
                        method: 'POST'
                    });
                    break;
                case 'storyline_improvement':
                    response = await Utils.apiRequest(`/novels/${novelId}/continuation/storyline/improve`, {
                        method: 'POST'
                    });
                    break;
                case 'quality_assessment':
                    response = await Utils.apiRequest(`/novels/${novelId}/continuation/quality`, {
                        method: 'POST',
                        body: JSON.stringify({ content_type: 'storyline' })
                    });
                    break;
                case 'content_improvement':
                    response = await Utils.apiRequest(`/novels/${novelId}/continuation/chapter/improve`, {
                        method: 'POST',
                        body: JSON.stringify({ suggestions: [] })
                    });
                    break;
                case 'chapter_writing':
                    response = await Utils.apiRequest(`/novels/${novelId}/continuation/chapter`, {
                        method: 'POST'
                    });
                    
                    // 章节写作完成后，自动保存章节
                    if (response.success) {
                        console.log('章节写作完成，开始保存章节...');
                        const saveResponse = await Utils.apiRequest(`/novels/${novelId}/continuation/save`, {
                            method: 'POST'
                        });
                        
                        if (saveResponse.success) {
                            console.log('章节保存成功');
                        } else {
                            console.error('章节保存失败:', saveResponse.error);
                            Utils.showMessage('章节保存失败: ' + saveResponse.error, 'warning');
                        }
                    }
                    break;
                case 'chapter_quality_assessment':
                    response = await Utils.apiRequest(`/novels/${novelId}/continuation/quality`, {
                        method: 'POST',
                        body: JSON.stringify({ content_type: 'story' })
                    });
                    break;
                case 'chapter_save':
                    response = await Utils.apiRequest(`/novels/${novelId}/continuation/save`, {
                        method: 'POST'
                    });
                    break;
                case 'chapter_completed':
                    // 续写完成状态，不需要执行任何操作
                    Utils.showMessage('续写章节已完成！', 'success');
                    return;
                default:
                    throw new Error('未知的续写步骤: ' + stepName);
            }
            
            if (response.success) {
                const stepNames = {
                    'storyline_generation': '续写故事线生成',
                    'quality_assessment': '故事线质量评估',
                    'storyline_improvement': '故事线优化',
                    'chapter_writing': '续写章节写作',
                    'chapter_quality_assessment': '章节质量评估',
                    'content_improvement': '章节内容优化',
                    'chapter_save': '章节保存',
                    'chapter_completed': '续写完成'
                };
                const friendlyName = stepNames[stepName] || stepName;
                Utils.showMessage(`${friendlyName}执行成功！`, 'success');
                
                // 如果是续写完成，刷新相关数据
                if (stepName === 'chapter_completed') {
                    console.log('普通续写完成，开始刷新相关数据...');
                    await refreshNovelDataAfterCompletion(novelId);
                }
                
                await ContinuationManager.loadContinuationWorkflow(novelId);
            }
        } catch (error) {
            Utils.showMessage(`执行${stepName}失败: ` + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 显示函数
const displayNovelList = (novels) => {
    const container = document.getElementById('novels-container');
    
    if (novels.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-book-open fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">暂无小说项目</h5>
                <p class="text-muted">点击"开始创作"创建您的第一部小说</p>
            </div>
        `;
        return;
    }
    
    const novelsHtml = novels.map(novel => `
        <div class="novel-item">
            <div class="novel-header">
                <h5 class="novel-title">${novel.title}</h5>
                <div class="novel-meta">
                    <i class="fas fa-calendar me-1"></i>
                    创建时间: ${Utils.formatDate(novel.created_at)}
                    <span class="ms-3">
                        <i class="fas fa-tag me-1"></i>
                        状态: ${novel.status}
                    </span>
                </div>
            </div>
            <div class="novel-body">
                <div class="novel-stats">
                    <div class="stat-item">
                        <div class="stat-value">${novel.chapters ? novel.chapters.length : 0}</div>
                        <div class="stat-label">章节数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${novel.novel_id.substring(0, 8)}...</div>
                        <div class="stat-label">项目ID</div>
                    </div>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-success btn-sm" onclick="startContinuationFromList('${novel.novel_id}')">
                        <i class="fas fa-edit me-1"></i>续写
                    </button>
                    <button class="btn btn-info btn-sm" onclick="viewNovelDetails('${novel.novel_id}')">
                        <i class="fas fa-eye me-1"></i>查看详情
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="deleteNovel('${novel.novel_id}', '${novel.title}')" title="删除小说">
                        <i class="fas fa-trash me-1"></i>删除
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = novelsHtml;
};

// 显示续写小说列表
const displayContinuationNovelList = (novels) => {
    console.log('displayContinuationNovelList 被调用，小说数量:', novels.length);
    const container = document.getElementById('novel-list');
    console.log('容器元素:', container);
    
    if (!container) {
        console.error('找不到 novel-list 容器元素');
        return;
    }
    
    if (novels.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-book-open fa-2x text-muted mb-3"></i>
                <h6 class="text-muted">暂无小说项目</h6>
                <p class="text-muted small">请先创建一部小说，然后才能进行续写</p>
            </div>
        `;
        return;
    }
    
    const novelsHtml = novels.map(novel => `
        <div class="list-group-item">
            <div class="d-flex w-100 justify-content-between align-items-start">
                <div class="flex-grow-1" style="cursor: pointer;" onclick="selectNovel('${novel.novel_id}')">
                    <h6 class="mb-1">${novel.title}</h6>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div>
                            <span class="badge bg-primary me-2">${novel.chapters ? novel.chapters.length : 0} 章节</span>
                            <span class="badge bg-secondary">${novel.status}</span>
                        </div>
                        <small class="text-muted">ID: ${novel.novel_id.substring(0, 8)}...</small>
                    </div>
                    <small class="text-muted">${Utils.formatDate(novel.created_at)}</small>
                </div>
                <div class="ms-2">
                    <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteNovel('${novel.novel_id}', '${novel.title}')" title="删除小说">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = novelsHtml;
};

const displayCreationWorkflow = (workflowData) => {
    const container = document.getElementById('workflow-container');
    
    const steps = [
        { key: 'tag_selection', name: '标签选择', icon: 'fas fa-tags' },
        { key: 'character_creation', name: '人物创建', icon: 'fas fa-users' },
        { key: 'storyline_generation', name: '故事线生成', icon: 'fas fa-route' },
        { key: 'knowledge_graph_creation', name: '知识图谱创建', icon: 'fas fa-project-diagram' },
        { key: 'chapter_writing', name: '章节写作', icon: 'fas fa-pen-fancy' },
        { key: 'chapter_completed', name: '创作完成', icon: 'fas fa-check-circle' }
    ];
    
    const currentStep = workflowData.current_step;
    
    const stepsHtml = steps.map(step => {
        let status = 'pending';
        let statusClass = 'pending';
        
        const currentStepIndex = steps.findIndex(s => s.key === currentStep);
        const stepIndex = steps.indexOf(step);
        
        if (stepIndex < currentStepIndex) {
            // 当前步骤之前的步骤都是已完成
            status = 'completed';
            statusClass = 'completed';
        } else if (stepIndex === currentStepIndex) {
            // 当前步骤
            status = 'current';
            statusClass = 'current';
        } else {
            // 当前步骤之后的步骤都是等待中
            status = 'pending';
            statusClass = 'pending';
        }
        
        return `
            <div class="workflow-step ${statusClass}">
                <div class="step-header" onclick="${status === 'completed' ? `toggleStepDetails('${step.key}')` : ''}" style="${status === 'completed' ? 'cursor: pointer;' : ''}">
                    <div class="step-icon ${statusClass}">
                        <i class="${step.icon}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h5 class="step-title">${step.name}</h5>
                        <p class="step-description">
                            ${status === 'completed' ? '已完成' : 
                              status === 'current' ? '进行中' : '等待中'}
                        </p>
                    </div>
                    ${status === 'completed' ? `
                        <div class="step-actions">
                            <i class="fas fa-chevron-down step-toggle-icon" id="toggle-icon-${step.key}"></i>
                        </div>
                    ` : ''}
                </div>
                
                ${status === 'completed' ? `
                    <div class="step-details" id="step-details-${step.key}" style="display: none;">
                        <div class="step-content">
                            <div class="loading-placeholder">
                                <i class="fas fa-spinner fa-spin me-2"></i>
                                正在加载详细内容...
                            </div>
                        </div>
                    </div>
                ` : ''}
                
                ${status === 'current' && step.key !== 'chapter_completed' ? `
                    <div class="d-flex gap-2">
                        <button class="btn btn-primary" onclick="executeStep('${step.key}')">
                            <i class="fas fa-play me-2"></i>执行此步骤
                        </button>
                    </div>
                ` : ''}
                ${status === 'current' && step.key === 'chapter_completed' ? `
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        恭喜！小说创作已完成！您可以查看章节内容或开始续写。
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    container.innerHTML = `
        <div class="mb-4">
            <h5>小说项目: ${workflowData.workflow_state?.title || '未知'}</h5>
            <p class="text-muted">项目ID: ${workflowData.novel_id}</p>
        </div>
        ${stepsHtml}
    `;
};

// 推断步骤状态的辅助函数
const inferStepStatus = (stepKey, currentStep) => {
    // 定义步骤的逻辑顺序和依赖关系
    const stepOrder = {
        'storyline_generation': 1,
        'quality_assessment': 2,
        'storyline_improvement': 3,
        'chapter_writing': 4,
        'chapter_quality_assessment': 5,
        'content_improvement': 6,
        'chapter_save': 7,
        'chapter_completed': 8
    };
    
    // 如果当前步骤不在定义中，尝试根据名称模式推断
    let currentStepOrder = stepOrder[currentStep];
    
    if (!currentStepOrder) {
        // 处理可能的步骤名称变体
        if (currentStep.includes('storyline')) {
            if (currentStep.includes('improvement')) {
                currentStepOrder = stepOrder['storyline_improvement'];
            } else if (currentStep.includes('quality') || currentStep.includes('assessment')) {
                currentStepOrder = stepOrder['quality_assessment'];
            } else {
                currentStepOrder = stepOrder['storyline_generation'];
            }
        } else if (currentStep.includes('chapter')) {
            if (currentStep.includes('save')) {
                currentStepOrder = stepOrder['chapter_save'];
            } else if (currentStep.includes('quality') || currentStep.includes('assessment')) {
                currentStepOrder = stepOrder['chapter_quality_assessment'];
            } else if (currentStep.includes('completed')) {
                currentStepOrder = stepOrder['chapter_completed'];
            } else if (currentStep.includes('improvement')) {
                currentStepOrder = stepOrder['content_improvement'];
            } else {
                currentStepOrder = stepOrder['chapter_writing'];
            }
        } else if (currentStep.includes('content') && currentStep.includes('improvement')) {
            currentStepOrder = stepOrder['content_improvement'];
        }
    }
    
    const stepKeyOrder = stepOrder[stepKey];
    
    if (!currentStepOrder || !stepKeyOrder) {
        return 'pending'; // 无法推断时默认为待处理
    }
    
    if (stepKeyOrder < currentStepOrder) {
        return 'completed';
    } else if (stepKeyOrder === currentStepOrder) {
        return 'current';
    } else {
        return 'pending';
    }
};

// 改进的推断步骤状态函数，支持跳过状态
const inferStepStatusWithSkip = (stepKey, currentStep, steps) => {
    const step = steps.find(s => s.key === stepKey);
    const currentStepObj = steps.find(s => s.key === currentStep);
    
    // 如果找不到步骤定义，使用基础推断
    if (!step) {
        return inferStepStatus(stepKey, currentStep);
    }
    
    const stepOrder = {
        'storyline_generation': 1,
        'quality_assessment': 2,
        'storyline_improvement': 3,
        'chapter_writing': 4,
        'chapter_quality_assessment': 5,
        'content_improvement': 6,
        'chapter_save': 7,
        'chapter_completed': 8
    };
    
    const stepKeyOrder = stepOrder[stepKey];
    let currentStepOrder = stepOrder[currentStep];
    
    // 如果当前步骤不在定义中，使用模糊匹配
    if (!currentStepOrder) {
        currentStepOrder = inferCurrentStepOrder(currentStep, stepOrder);
    }
    
    if (!currentStepOrder || !stepKeyOrder) {
        return 'pending';
    }
    
    if (stepKeyOrder < currentStepOrder) {
        // 对于条件性步骤，如果被跳过了，显示为"已跳过"
        if (step.conditional && !wasStepExecuted(stepKey, currentStep)) {
            return 'skipped';
        }
        return 'completed';
    } else if (stepKeyOrder === currentStepOrder) {
        return 'current';
    } else {
        return 'pending';
    }
};

// 推断当前步骤的顺序号
const inferCurrentStepOrder = (currentStep, stepOrder) => {
    if (currentStep.includes('storyline')) {
        if (currentStep.includes('improvement')) {
            return stepOrder['storyline_improvement'];
        } else if (currentStep.includes('quality') || currentStep.includes('assessment')) {
            return stepOrder['quality_assessment'];
        } else {
            return stepOrder['storyline_generation'];
        }
    } else if (currentStep.includes('chapter')) {
        if (currentStep.includes('save')) {
            return stepOrder['chapter_save'];
        } else if (currentStep.includes('quality') || currentStep.includes('assessment')) {
            return stepOrder['chapter_quality_assessment'];
        } else if (currentStep.includes('completed')) {
            return stepOrder['chapter_completed'];
        } else if (currentStep.includes('improvement')) {
            return stepOrder['content_improvement'];
        } else {
            return stepOrder['chapter_writing'];
        }
    } else if (currentStep.includes('content') && currentStep.includes('improvement')) {
        return stepOrder['content_improvement'];
    }
    return null;
};

// 检查步骤是否被执行过
const wasStepExecuted = (stepKey, currentStep) => {
    // 简单的启发式判断：如果当前步骤包含了该步骤的关键词，说明执行过
    if (stepKey === 'storyline_improvement') {
        return currentStep.includes('storyline') && currentStep.includes('improvement');
    } else if (stepKey === 'content_improvement') {
        return currentStep.includes('content') && currentStep.includes('improvement');
    }
    return false;
};

const displayContinuationWorkflow = (continuationData) => {
    const container = document.getElementById('continuation-container');
    
    // 增强的小说信息展示
    const novelInfoHtml = `
        <div class="novel-info-enhanced mb-4">
            <div class="card border-0 shadow-sm">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h4 class="novel-title-enhanced mb-2">
                                <i class="fas fa-book-open text-primary me-2"></i>
                                ${continuationData.novel_title || '未知小说'}
                            </h4>
                            <div class="novel-stats d-flex flex-wrap gap-3 mb-2">
                                <span class="stat-item">
                                    <i class="fas fa-chapter text-info me-1"></i>
                                    已写章节: <strong>${continuationData.chapter_count || 0}</strong>
                                </span>
                                <span class="stat-item">
                                    <i class="fas fa-calendar text-success me-1"></i>
                                    最后更新: <strong>今天</strong>
                                </span>
                                <span class="stat-item">
                                    <i class="fas fa-clock text-warning me-1"></i>
                                    状态: <strong>${continuationData.current_step === 'chapter_completed' ? '已完成' : '进行中'}</strong>
                                </span>
                            </div>
                            ${continuationData.user_requirements ? `
                                <div class="continuation-requirements">
                                    <small class="text-muted">
                                        <i class="fas fa-edit me-1"></i>
                                        续写需求: ${continuationData.user_requirements}
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                        <div class="col-md-4 text-end">
                            ${continuationData.current_step === 'chapter_completed' ? `
                                <div class="d-flex flex-column gap-2">
                                    <button class="btn btn-primary btn-lg" onclick="startNextChapter()">
                                        <i class="fas fa-plus-circle me-2"></i>
                                        写下一章
                                    </button>
           <button class="btn btn-success btn-sm" onclick="showQuickContinuationDialog()">
               <i class="fas fa-bolt me-2"></i>
               快速续写
           </button>
           <button class="btn btn-info btn-sm" onclick="checkQuickContinuationProgress()">
               <i class="fas fa-chart-line me-2"></i>
               查看进度
           </button>
                                </div>
                            ` : `
                                <button class="btn btn-secondary btn-lg" disabled>
                                    <i class="fas fa-clock me-2"></i>
                                    续写进行中
                                </button>
                            `}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 参考新书开发的UI设计，使用类似的工作流显示
    const steps = [
        { key: 'storyline_generation', name: '续写故事线生成', icon: 'fas fa-route', description: 'AI分析现有故事并生成续写大纲' },
        { key: 'chapter_writing', name: '续写章节写作', icon: 'fas fa-pen-fancy', description: '根据故事线创作新的章节内容' },
        { key: 'chapter_completed', name: '续写完成', icon: 'fas fa-flag-checkered', description: '章节已保存，可以继续续写' }
    ];
    
    const currentStep = continuationData.current_step;
    
    const stepsHtml = steps.map(step => {
        let status = 'pending';
        let statusClass = 'pending';
        
        const currentStepIndex = steps.findIndex(s => s.key === currentStep);
        const stepIndex = steps.indexOf(step);
        
        // 处理当前步骤
        if (step.key === currentStep) {
            if (currentStep === 'chapter_completed') {
                status = 'completed';
                statusClass = 'completed';
            } else {
                status = 'current';
                statusClass = 'current';
            }
        } 
        // 处理已完成步骤
        else if (currentStepIndex >= 0 && stepIndex < currentStepIndex) {
            status = 'completed';
            statusClass = 'completed';
        }
        // 处理未找到当前步骤的情况（后端设置了前端未定义的步骤）
        else if (currentStepIndex === -1) {
            // 智能推断：根据后端步骤名称推断前端步骤状态
            if (currentStep.includes('storyline')) {
                // 后端在处理故事线相关步骤
                if (step.key === 'storyline_generation') {
                    status = 'completed';  // 故事线生成已完成
                    statusClass = 'completed';
                } else if (step.key === 'chapter_writing') {
                    status = 'current';    // 下一步是章节写作
                    statusClass = 'current';
                }
            } else if (currentStep.includes('chapter') || currentStep.includes('content')) {
                // 后端在处理章节相关步骤
                if (step.key === 'storyline_generation') {
                    status = 'completed';  // 故事线生成已完成
                    statusClass = 'completed';
                } else if (step.key === 'chapter_writing') {
                    status = 'completed';  // 章节写作已完成
                    statusClass = 'completed';
                }
            } else if (currentStep.includes('save')) {
                // 后端在保存步骤
                if (step.key === 'storyline_generation') {
                    status = 'completed';
                    statusClass = 'completed';
                } else if (step.key === 'chapter_writing') {
                    status = 'completed';
                    statusClass = 'completed';
                } else if (step.key === 'chapter_completed') {
                    status = 'current';
                    statusClass = 'current';
                }
            }
        }
        
        return `
            <div class="workflow-step ${statusClass}">
                <div class="step-header" onclick="${status === 'completed' ? `toggleStepDetails('${step.key}')` : ''}" style="${status === 'completed' ? 'cursor: pointer;' : ''}">
                    <div class="step-icon ${statusClass}">
                        <i class="${step.icon}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h5 class="step-title">${step.name}</h5>
                        <p class="step-description">
                            ${step.description}
                        </p>
                        <div class="step-status">
                            <span class="badge bg-${status === 'completed' ? 'success' : status === 'current' ? 'primary' : 'secondary'}">
                                ${status === 'completed' ? '已完成' : 
                                  status === 'current' ? '进行中' : '等待中'}
                            </span>
                        </div>
                    </div>
                    ${status === 'completed' ? `
                        <div class="step-actions">
                            <i class="fas fa-chevron-down step-toggle-icon" id="toggle-icon-${step.key}"></i>
                        </div>
                    ` : ''}
                </div>
                
                ${status === 'completed' ? `
                    <div class="step-details" id="step-details-${step.key}" style="display: none;">
                        <div class="step-content">
                            <div class="loading-placeholder">
                                <i class="fas fa-spinner fa-spin me-2"></i>
                                正在加载详细内容...
                            </div>
                        </div>
                    </div>
                ` : ''}
                
                ${status === 'current' && step.key !== 'chapter_completed' ? `
                    <div class="step-actions-current">
                        <button class="btn btn-success btn-lg" onclick="executeContinuationStep('${step.key}')">
                            <i class="fas fa-play me-2"></i>执行此步骤
                        </button>
                        
                        <!-- 优化选项 -->
                        ${step.key === 'storyline_generation' ? `
                            <div class="optimization-options mt-2">
                                <button class="btn btn-outline-warning btn-sm me-2" onclick="optimizeContinuationStorylineBasedOnQuality()">
                                    <i class="fas fa-magic me-1"></i>智能优化故事线
                                </button>
                                <button class="btn btn-outline-info btn-sm" onclick="improveContinuationStep('storyline_generation')">
                                    <i class="fas fa-edit me-1"></i>手动改进故事线
                                </button>
                            </div>
                        ` : ''}
                        
                        ${step.key === 'chapter_writing' ? `
                            <div class="optimization-options mt-2">
                                <button class="btn btn-outline-info btn-sm" onclick="improveContinuationStep('chapter_writing')">
                                    <i class="fas fa-edit me-1"></i>改进章节内容
                                </button>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                
                ${status === 'current' && step.key === 'chapter_completed' ? `
                    <div class="step-completed-message">
                        <div class="alert alert-success border-0">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-check-circle fa-2x text-success me-3"></i>
                                <div>
                                    <h6 class="mb-1">续写章节已完成！</h6>
                                    <p class="mb-0">章节已保存，您可以继续续写下一章或查看内容。</p>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 完成后的操作选项 -->
                        <div class="completion-actions mt-3">
                            <button class="btn btn-primary btn-lg me-2" onclick="startNextChapter()">
                                <i class="fas fa-plus-circle me-2"></i>开始下一章
                            </button>
                            <button class="btn btn-success btn-sm me-2" onclick="showQuickContinuationDialog()">
                                <i class="fas fa-bolt me-2"></i>快速续写
                            </button>
                            <button class="btn btn-info btn-sm me-2" onclick="checkQuickContinuationProgress()">
                                <i class="fas fa-chart-line me-2"></i>查看进度
                            </button>
                            <button class="btn btn-outline-danger btn-sm" onclick="clearContinuationChapterCache()">
                                <i class="fas fa-trash me-2"></i>清除缓存
                            </button>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    container.innerHTML = `
        ${novelInfoHtml}
        <div class="workflow-steps">
            ${stepsHtml}
        </div>
    `;
};

// 步骤详情管理
const StepDetailsManager = {
    // 通用的错误处理包装器
    withErrorHandling: async (loadFunction, contentElement, stepName, stepKey) => {
        try {
            await loadFunction(contentElement);
        } catch (error) {
            console.error(`加载${stepName}详情失败:`, error);
            contentElement.innerHTML = `
                <div class="step-detail-content">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        ${stepName}数据不存在或尚未生成。请先完成相关步骤。
                    </div>
                    <div class="step-actions">
                        <button class="btn btn-warning btn-sm" onclick="regenerateStep('${stepKey}')">
                            <i class="fas fa-redo me-2"></i>重新生成
                        </button>
                    </div>
                </div>
            `;
        }
    },

    // 切换步骤详情显示
    toggleStepDetails: async (stepKey) => {
        const detailsElement = document.getElementById(`step-details-${stepKey}`);
        const toggleIcon = document.getElementById(`toggle-icon-${stepKey}`);
        
        if (!detailsElement) {
            console.error(`未找到步骤详情元素: step-details-${stepKey}`);
            return;
        }
        
        if (detailsElement.style.display === 'none') {
            // 展开详情
            detailsElement.style.display = 'block';
            if (toggleIcon) {
                toggleIcon.classList.remove('fa-chevron-down');
                toggleIcon.classList.add('fa-chevron-up');
            }
            
            // 加载详细内容
            await StepDetailsManager.loadStepDetails(stepKey);
        } else {
            // 收起详情
            detailsElement.style.display = 'none';
            if (toggleIcon) {
                toggleIcon.classList.remove('fa-chevron-up');
                toggleIcon.classList.add('fa-chevron-down');
            }
        }
    },
    
    // 加载步骤详细内容
    loadStepDetails: async (stepKey) => {
        if (!AppState.currentNovelId) return;
        
        try {
            const contentElement = document.querySelector(`#step-details-${stepKey} .step-content`);
            
            // 检查是否在续写模式
            const isContinuationMode = AppState.continuationData && AppState.continuationData.is_continuation;
            
            // 根据步骤类型和模式加载不同的内容
            switch (stepKey) {
                case 'tag_selection':
                    await StepDetailsManager.withErrorHandling(
                        StepDetailsManager.loadTagDetails, 
                        contentElement, 
                        '标签', 
                        stepKey
                    );
                    break;
                case 'character_creation':
                    await StepDetailsManager.withErrorHandling(
                        StepDetailsManager.loadCharacterDetails, 
                        contentElement, 
                        '人物', 
                        stepKey
                    );
                    break;
                case 'storyline_generation':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationStorylineDetails(contentElement);
                    } else {
                    await StepDetailsManager.loadStorylineDetails(contentElement);
                    }
                    break;
                case 'knowledge_graph_creation':
                    await StepDetailsManager.loadKnowledgeGraphDetails(contentElement);
                    break;
                case 'chapter_writing':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationChapterDetails(contentElement);
                    } else {
                    await StepDetailsManager.loadChapterDetails(contentElement);
                    }
                    break;
                // 续写专用步骤
                case 'storyline_improvement':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationStorylineImprovementDetails(contentElement);
                    }
                    break;
                case 'quality_assessment':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationQualityAssessmentDetails(contentElement);
                    }
                    break;
                case 'chapter_quality_assessment':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationChapterQualityDetails(contentElement);
                    }
                    break;
                case 'content_improvement':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationContentImprovementDetails(contentElement);
                    }
                    break;
                case 'chapter_save':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationChapterSaveDetails(contentElement);
                    }
                    break;
                case 'chapter_completed':
                    if (isContinuationMode) {
                        await StepDetailsManager.loadContinuationChapterCompletedDetails(contentElement);
                    }
                    break;
            }
        } catch (error) {
            console.error('加载步骤详情失败:', error);
            const contentElement = document.querySelector(`#step-details-${stepKey} .step-content`);
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    加载详细内容失败: ${error.message}
                </div>
            `;
        }
    },
    
    // 加载续写完成详情
    loadContinuationChapterCompletedDetails: async (contentElement) => {
        try {
            // 获取最新的章节数据
            const chaptersResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/chapters`);
            if (!chaptersResponse.success || chaptersResponse.data.length === 0) {
                contentElement.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        未找到续写章节数据
                    </div>
                `;
                return;
            }
            
            const latestChapter = chaptersResponse.data[chaptersResponse.data.length - 1];
            
            // 获取质量评估数据
            let qualityAssessment = null;
            try {
                const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/continuation_chapter_quality_assessment`);
                if (qualityResponse.success) {
                    qualityAssessment = qualityResponse.data;
                }
            } catch (error) {
                console.log('未找到续写章节质量评估数据');
            }
            
            contentElement.innerHTML = `
                <div class="step-detail-content">
                    <h6><i class="fas fa-flag-checkered me-2"></i>续写完成</h6>
                    
                    <div class="completion-summary mb-4">
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i>
                            <strong>续写章节已完成！</strong>
                            <p class="mb-0 mt-2">第${latestChapter.chapter_number}章已成功生成并保存。</p>
                        </div>
                    </div>
                    
                    <div class="chapter-summary mb-4">
                        <h6><i class="fas fa-book me-2"></i>章节信息</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>标题：</strong>${latestChapter.title}</p>
                                <p><strong>字数：</strong>${latestChapter.word_count || 0}</p>
                                <p><strong>创建时间：</strong>${Utils.formatDate(latestChapter.created_at)}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>章节概要：</strong></p>
                                <p class="text-muted">${latestChapter.summary || '暂无概要'}</p>
                            </div>
                        </div>
                    </div>
                    
                    ${Utils.generateQualityAssessmentHTML(qualityAssessment)}
                    
                    <div class="chapter-actions mb-3">
                        <button class="btn btn-outline-primary btn-sm" onclick="showContinuationChapterModal('${AppState.currentNovelId}')">
                            <i class="fas fa-eye me-1"></i>查看完整内容
                        </button>
                        <button class="btn btn-outline-info btn-sm" onclick="assessContinuationQuality('story')">
                            <i class="fas fa-star me-1"></i>质量评估
                        </button>
                        <button class="btn btn-outline-success btn-sm" onclick="regenerateContinuationStep('chapter_writing')">
                            <i class="fas fa-redo me-1"></i>重新生成章节
                        </button>
                    </div>
                    
                    <div class="next-steps">
                        <h6><i class="fas fa-arrow-right me-2"></i>下一步操作</h6>
                        <div class="list-group">
                            <div class="list-group-item">
                                <i class="fas fa-plus-circle me-2 text-success"></i>
                                <strong>继续续写</strong> - 生成下一章内容
                            </div>
                            <div class="list-group-item">
                                <i class="fas fa-edit me-2 text-primary"></i>
                                <strong>编辑修改</strong> - 对当前章节进行修改
                            </div>
                            <div class="list-group-item">
                                <i class="fas fa-download me-2 text-info"></i>
                                <strong>导出小说</strong> - 下载完整小说文件
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('加载续写完成详情失败:', error);
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    加载续写完成详情失败: ${error.message}
                </div>
            `;
        }
    },
    
    // 加载标签详情
    loadTagDetails: async (contentElement) => {
        try {
            const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/tags`);
            
            if (response.success) {
                const tags = response.data;
                
                // 获取所有可用的标签分类
                const tagCategoriesResponse = await Utils.apiRequest('/config/tags');
                const availableCategories = tagCategoriesResponse.success ? tagCategoriesResponse.data : {};
                
                contentElement.innerHTML = `
                    <div class="step-detail-content">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6><i class="fas fa-tags me-2"></i>已选择的标签</h6>
                            <div class="step-controls">
                                <button class="btn btn-outline-primary btn-sm" onclick="toggleTagEditMode()">
                                    <i class="fas fa-edit me-1"></i>编辑标签
                                </button>
                                <button class="btn btn-outline-success btn-sm" onclick="showAddTagModal()">
                                    <i class="fas fa-plus me-1"></i>添加标签
                                </button>
                            </div>
                        </div>
                        
                        <div class="tags-display" id="tags-display">
                            ${Object.entries(tags.selected_tags || {}).map(([category, tagList]) => `
                                <div class="tag-category" data-category="${category}">
                                    <strong>${category}:</strong>
                                    <div class="tag-list">
                                        ${tagList.map(tag => `
                                            <span class="tag" data-category="${category}" data-tag="${tag}">
                                                ${tag}
                                                <i class="fas fa-times tag-remove" onclick="removeTag('${category}', '${tag}')" style="display: none;"></i>
                                            </span>
                                        `).join('')}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        
                        <div class="step-actions mt-3">
                            <button class="btn btn-warning btn-sm" onclick="regenerateStep('tag_selection')">
                                <i class="fas fa-redo me-2"></i>重新生成标签
                            </button>
                            <button class="btn btn-success btn-sm" onclick="saveTagChanges()" style="display: none;" id="save-tags-btn">
                                <i class="fas fa-save me-2"></i>保存标签修改
                            </button>
                        </div>
                    </div>
                `;
            } else {
                // 显示错误信息
                contentElement.innerHTML = `
                    <div class="step-detail-content">
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            标签数据不存在或尚未生成。请重新生成标签。
                        </div>
                        <div class="step-actions">
                            <button class="btn btn-warning btn-sm" onclick="regenerateStep('tag_selection')">
                                <i class="fas fa-redo me-2"></i>重新生成标签
                            </button>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('加载标签详情失败:', error);
            contentElement.innerHTML = `
                <div class="step-detail-content">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        加载详细内容失败: ${error.message}
                    </div>
                    <div class="step-actions">
                        <button class="btn btn-warning btn-sm" onclick="regenerateStep('tag_selection')">
                            <i class="fas fa-redo me-2"></i>重新生成标签
                        </button>
                    </div>
                </div>
            `;
        }
    },
    
    // 加载人物详情
    loadCharacterDetails: async (contentElement) => {
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/characters`);
        
        if (response.success) {
            const characters = response.data;
            
            // 加载质量评估
            let qualityAssessment = null;
            try {
                const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/character_quality_assessment`);
                if (qualityResponse.success) {
                    qualityAssessment = qualityResponse.data;
                }
            } catch (error) {
                console.log('未找到质量评估数据');
            }
            
            contentElement.innerHTML = `
                <div class="step-detail-content">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6><i class="fas fa-users me-2"></i>人物设定</h6>
                        <div class="step-controls">
                            <button class="btn btn-outline-primary btn-sm" onclick="toggleEditMode('character_creation')">
                                <i class="fas fa-edit me-1"></i>编辑
                            </button>
                            <button class="btn btn-outline-info btn-sm" onclick="assessQuality('character_creation')">
                                <i class="fas fa-star me-1"></i>质量评估
                            </button>
                        </div>
                    </div>
                    
                    ${Utils.generateQualityAssessmentHTML(qualityAssessment, false)}
                    
                    <div class="character-details" id="character-content">
                        <div class="main-character mb-4">
                            <h6 class="text-primary">主角</h6>
                            <div class="character-card">
                                <!-- 基本信息 -->
                                <div class="character-section">
                                    <h6 class="section-title">基本信息</h6>
                                <div class="character-basic">
                                    <strong>姓名:</strong> <span class="editable" data-field="main_character.basic_info.name">${characters.main_character?.basic_info?.name || '未知'}</span><br>
                                    <strong>年龄:</strong> <span class="editable" data-field="main_character.basic_info.age">${characters.main_character?.basic_info?.age || '未知'}</span><br>
                                        <strong>性别:</strong> <span class="editable" data-field="main_character.basic_info.gender">${characters.main_character?.basic_info?.gender || '未知'}</span><br>
                                    <strong>职业:</strong> <span class="editable" data-field="main_character.basic_info.occupation">${characters.main_character?.basic_info?.occupation || '未知'}</span>
                                </div>
                                </div>
                                
                                <!-- 性格特征 -->
                                <div class="character-section">
                                    <h6 class="section-title">性格特征</h6>
                                    <div class="personality-grid">
                                        <div class="personality-item">
                                            <strong>外向性:</strong> <span class="editable" data-field="main_character.personality.extraversion">${characters.main_character?.personality?.extraversion || '未知'}</span>
                                        </div>
                                        <div class="personality-item">
                                            <strong>宜人性:</strong> <span class="editable" data-field="main_character.personality.agreeableness">${characters.main_character?.personality?.agreeableness || '未知'}</span>
                                        </div>
                                        <div class="personality-item">
                                            <strong>尽责性:</strong> <span class="editable" data-field="main_character.personality.conscientiousness">${characters.main_character?.personality?.conscientiousness || '未知'}</span>
                                        </div>
                                        <div class="personality-item">
                                            <strong>神经质:</strong> <span class="editable" data-field="main_character.personality.neuroticism">${characters.main_character?.personality?.neuroticism || '未知'}</span>
                                        </div>
                                        <div class="personality-item">
                                            <strong>开放性:</strong> <span class="editable" data-field="main_character.personality.openness">${characters.main_character?.personality?.openness || '未知'}</span>
                                        </div>
                                </div>
                                <div class="character-description mt-2">
                                        <strong>性格描述:</strong> 
                                        <span class="editable" data-field="main_character.personality.description">${characters.main_character?.personality?.description || '未知'}</span>
                                    </div>
                                </div>
                                
                                <!-- 外貌特征 -->
                                <div class="character-section">
                                    <h6 class="section-title">外貌特征</h6>
                                    <div class="character-basic">
                                        <strong>身高:</strong> <span class="editable" data-field="main_character.appearance.height">${characters.main_character?.appearance?.height || '未知'}</span><br>
                                        <strong>体型:</strong> <span class="editable" data-field="main_character.appearance.build">${characters.main_character?.appearance?.build || '未知'}</span><br>
                                        <strong>着装风格:</strong> <span class="editable" data-field="main_character.appearance.clothing_style">${characters.main_character?.appearance?.clothing_style || '未知'}</span><br>
                                        <strong>标志性特征:</strong> 
                                        <span class="editable" data-field="main_character.appearance.distinctive_features" title="编辑提示：多个特征用逗号分隔">${Array.isArray(characters.main_character?.appearance?.distinctive_features) ? characters.main_character.appearance.distinctive_features.join(', ') : (characters.main_character?.appearance?.distinctive_features || '未知')}</span>
                                    </div>
                                </div>
                                
                                <!-- 背景故事 -->
                                <div class="character-section">
                                    <h6 class="section-title">背景故事</h6>
                                    <div class="character-description">
                                        <strong>核心欲望:</strong> <span class="editable" data-field="main_character.background.core_desire">${characters.main_character?.background?.core_desire || '未知'}</span><br>
                                        <strong>主要恐惧:</strong> <span class="editable" data-field="main_character.background.fear">${characters.main_character?.background?.fear || '未知'}</span><br>
                                        <strong>过往经历:</strong> <span class="editable" data-field="main_character.background.past_experience">${characters.main_character?.background?.past_experience || '未知'}</span><br>
                                        <strong>行为动机:</strong> <span class="editable" data-field="main_character.background.motivation">${characters.main_character?.background?.motivation || '未知'}</span><br>
                                        <strong>价值观:</strong> <span class="editable" data-field="main_character.background.values">${Array.isArray(characters.main_character?.background?.values) ? characters.main_character.background.values.join(', ') : (characters.main_character?.background?.values || '未知')}</span><br>
                                        <strong>创伤经历:</strong> <span class="editable" data-field="main_character.background.trauma">${characters.main_character?.background?.trauma || '未知'}</span><br>
                                        <strong>主要成就:</strong> <span class="editable" data-field="main_character.background.achievements">${Array.isArray(characters.main_character?.background?.achievements) ? characters.main_character.background.achievements.join('; ') : (characters.main_character?.background?.achievements || '未知')}</span>
                                    </div>
                                </div>
                                
                                <!-- 技能特长 -->
                                <div class="character-section">
                                    <h6 class="section-title">技能特长</h6>
                                    <div class="character-description">
                                        <strong>核心技能:</strong> <span class="editable" data-field="main_character.skills.core_skills" title="编辑提示：多个技能用逗号分隔">${Array.isArray(characters.main_character?.skills?.core_skills) ? characters.main_character.skills.core_skills.join(', ') : (characters.main_character?.skills?.core_skills || '未知')}</span><br>
                                        <strong>辅助技能:</strong> <span class="editable" data-field="main_character.skills.auxiliary_skills" title="编辑提示：多个技能用逗号分隔">${Array.isArray(characters.main_character?.skills?.auxiliary_skills) ? characters.main_character.skills.auxiliary_skills.join(', ') : (characters.main_character?.skills?.auxiliary_skills || '未知')}</span><br>
                                        <strong>隐藏技能:</strong> <span class="editable" data-field="main_character.skills.hidden_skills" title="编辑提示：多个技能用逗号分隔">${Array.isArray(characters.main_character?.skills?.hidden_skills) ? characters.main_character.skills.hidden_skills.join(', ') : (characters.main_character?.skills?.hidden_skills || '未知')}</span><br>
                                        <strong>技能等级:</strong><br>
                                        ${(() => {
                                            const skillLevels = characters.main_character?.skills?.skill_levels || {};
                                            if (typeof skillLevels === 'object' && Object.keys(skillLevels).length > 0) {
                                                return Object.entries(skillLevels).map(([skill, level]) => 
                                                    `&nbsp;&nbsp;• <span class="editable" data-field="main_character.skills.skill_levels.${skill}" title="技能名称">${skill}</span>: <span class="editable" data-field="main_character.skills.skill_levels.${skill}_level" title="技能等级">${level}</span><br>`
                                                ).join('');
                                            } else {
                                                return '&nbsp;&nbsp;• <span class="editable" data-field="main_character.skills.skill_levels" title="编辑提示：格式如 技能1:等级1, 技能2:等级2">未知</span><br>';
                                            }
                                        })()}
                                    </div>
                                </div>
                                
                                <!-- 人际关系 -->
                                <div class="character-section">
                                    <h6 class="section-title">人际关系</h6>
                                    <div class="character-description">
                                        <strong>家庭关系:</strong><br>
                                        &nbsp;&nbsp;• 父母: <span class="editable" data-field="main_character.relationships.family.parents">${characters.main_character?.relationships?.family?.parents || '未知'}</span><br>
                                        &nbsp;&nbsp;• 兄弟姐妹: <span class="editable" data-field="main_character.relationships.family.siblings">${characters.main_character?.relationships?.family?.siblings || '未知'}</span><br>
                                        &nbsp;&nbsp;• 其他亲属: <span class="editable" data-field="main_character.relationships.family.extended_family">${characters.main_character?.relationships?.family?.extended_family || '未知'}</span><br>
                                        
                                        <strong>朋友关系:</strong><br>
                                        &nbsp;&nbsp;• 密友: <span class="editable" data-field="main_character.relationships.friends.close_friends" title="编辑提示：多个朋友用逗号分隔">${Array.isArray(characters.main_character?.relationships?.friends?.close_friends) ? characters.main_character.relationships.friends.close_friends.join(', ') : (characters.main_character?.relationships?.friends?.close_friends || '未知')}</span><br>
                                        &nbsp;&nbsp;• 熟人: <span class="editable" data-field="main_character.relationships.friends.acquaintances" title="编辑提示：多个熟人用逗号分隔">${Array.isArray(characters.main_character?.relationships?.friends?.acquaintances) ? characters.main_character.relationships.friends.acquaintances.join(', ') : (characters.main_character?.relationships?.friends?.acquaintances || '未知')}</span><br>
                                        
                                        <strong>敌对关系:</strong><br>
                                        &nbsp;&nbsp;• 竞争对手: <span class="editable" data-field="main_character.relationships.enemies.rivals" title="编辑提示：多个对手用逗号分隔">${Array.isArray(characters.main_character?.relationships?.enemies?.rivals) ? characters.main_character.relationships.enemies.rivals.join(', ') : (characters.main_character?.relationships?.enemies?.rivals || '未知')}</span><br>
                                        &nbsp;&nbsp;• 敌对者: <span class="editable" data-field="main_character.relationships.enemies.antagonists" title="编辑提示：多个敌对者用逗号分隔">${Array.isArray(characters.main_character?.relationships?.enemies?.antagonists) ? characters.main_character.relationships.enemies.antagonists.join(', ') : (characters.main_character?.relationships?.enemies?.antagonists || '未知')}</span><br>
                                        
                                        <strong>感情状况:</strong> <span class="editable" data-field="main_character.relationships.romantic">${characters.main_character?.relationships?.romantic || '未知'}</span><br>
                                    </div>
                                </div>
                                
                                <!-- 角色弧线 -->
                                <div class="character-section">
                                    <h6 class="section-title">角色弧线</h6>
                                    <div class="character-description">
                                        <strong>起始点:</strong> <span class="editable" data-field="main_character.character_arc.starting_point">${characters.main_character?.character_arc?.starting_point || '未知'}</span><br>
                                        <strong>成长方向:</strong> <span class="editable" data-field="main_character.character_arc.growth_direction">${characters.main_character?.character_arc?.growth_direction || '未知'}</span><br>
                                        <strong>潜在冲突:</strong> <span class="editable" data-field="main_character.character_arc.potential_conflicts">${Array.isArray(characters.main_character?.character_arc?.potential_conflicts) ? characters.main_character.character_arc.potential_conflicts.join('; ') : (characters.main_character?.character_arc?.potential_conflicts || '未知')}</span><br>
                                        <strong>转变机会:</strong> <span class="editable" data-field="main_character.character_arc.transformation_opportunities">${Array.isArray(characters.main_character?.character_arc?.transformation_opportunities) ? characters.main_character.character_arc.transformation_opportunities.join('; ') : (characters.main_character?.character_arc?.transformation_opportunities || '未知')}</span>
                                    </div>
                                </div>
                                
                                <!-- 故事功能 -->
                                <div class="character-section">
                                    <h6 class="section-title">故事功能</h6>
                                    <div class="character-description">
                                        <strong>情节作用:</strong> <span class="editable" data-field="main_character.story_function.role_in_plot">${characters.main_character?.story_function?.role_in_plot || '未知'}</span><br>
                                        <strong>冲突生成:</strong> <span class="editable" data-field="main_character.story_function.conflict_generator">${characters.main_character?.story_function?.conflict_generator || '未知'}</span><br>
                                        <strong>主题代表:</strong> <span class="editable" data-field="main_character.story_function.theme_representative">${characters.main_character?.story_function?.theme_representative || '未知'}</span><br>
                                        <strong>读者连接:</strong> <span class="editable" data-field="main_character.story_function.reader_connection">${characters.main_character?.story_function?.reader_connection || '未知'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="supporting-characters">
                            <h6 class="text-secondary">配角</h6>
                            ${(() => {
                                const supportingChars = characters.supporting_characters || {};
                                // 处理对象格式的配角数据
                                const charArray = Array.isArray(supportingChars) ? supportingChars : Object.values(supportingChars);
                                return charArray.map((char, index) => `
                                    <div class="character-card mb-3">
                                        <!-- 基本信息 -->
                                        <div class="character-section">
                                            <h6 class="section-title">${char.basic_info?.name || '未知角色'}</h6>
                                        <div class="character-basic">
                                                <strong>姓名:</strong> <span class="editable" data-field="supporting_characters.${index}.basic_info.name">${char.basic_info?.name || '未知'}</span><br>
                                                <strong>年龄:</strong> <span class="editable" data-field="supporting_characters.${index}.basic_info.age">${char.basic_info?.age || '未知'}</span><br>
                                                <strong>性别:</strong> <span class="editable" data-field="supporting_characters.${index}.basic_info.gender">${char.basic_info?.gender || '未知'}</span><br>
                                                <strong>职业:</strong> <span class="editable" data-field="supporting_characters.${index}.basic_info.occupation">${char.basic_info?.occupation || '未知'}</span><br>
                                                <strong>角色定位:</strong> <span class="editable" data-field="supporting_characters.${index}.role">${char.role || '未知'}</span>
                                            </div>
                                        </div>
                                        
                                        <!-- 性格特征 -->
                                        <div class="character-section">
                                            <h6 class="section-title">性格特征</h6>
                                            <div class="character-description">
                                                <span class="editable" data-field="supporting_characters.${index}.personality">${char.personality || '未知'}</span>
                                            </div>
                                        </div>
                                        
                                        <!-- 外貌特征 -->
                                        <div class="character-section">
                                            <h6 class="section-title">外貌特征</h6>
                                            <div class="character-description">
                                                <span class="editable" data-field="supporting_characters.${index}.appearance">${char.appearance || '未知'}</span>
                                            </div>
                                        </div>
                                        
                                        <!-- 背景故事 -->
                                        <div class="character-section">
                                            <h6 class="section-title">背景故事</h6>
                                            <div class="character-description">
                                                <span class="editable" data-field="supporting_characters.${index}.background">${char.background || '未知'}</span>
                                            </div>
                                        </div>
                                        
                                        <!-- 与主角关系 -->
                                        <div class="character-section">
                                            <h6 class="section-title">与主角关系</h6>
                                            <div class="character-description">
                                                <span class="editable" data-field="supporting_characters.${index}.relationship_with_main">${char.relationship_with_main || '未知'}</span>
                                            </div>
                                        </div>
                                    </div>
                                `).join('');
                            })()}
                        </div>
                    </div>
                    
                    <div class="step-actions mt-3">
                        <button class="btn btn-warning btn-sm" onclick="regenerateStep('character_creation')">
                            <i class="fas fa-redo me-2"></i>重新生成人物
                        </button>
                        <button class="btn btn-info btn-sm" onclick="improveStep('character_creation')">
                            <i class="fas fa-magic me-2"></i>改进人物
                        </button>
                        <button class="btn btn-primary btn-sm" onclick="optimizeCharactersBasedOnQuality()">
                            <i class="fas fa-star me-2"></i>基于质量评估优化
                        </button>
                        <button class="btn btn-success btn-sm" onclick="saveStepContent('character_creation')" style="display: none;" id="save-character-creation-btn">
                            <i class="fas fa-save me-2"></i>保存修改
                        </button>
                    </div>
                </div>
            `;
        }
    },
    
    // 加载故事线详情
    loadStorylineDetails: async (contentElement) => {
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/storyline`);
        
        if (response.success) {
            const storyline = response.data;
            
            // 加载质量评估
            let qualityAssessment = null;
            try {
                const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/storyline_quality_assessment`);
                if (qualityResponse.success) {
                    qualityAssessment = qualityResponse.data;
                }
            } catch (error) {
                console.log('未找到质量评估数据');
            }
            
            contentElement.innerHTML = `
                <div class="step-detail-content">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6><i class="fas fa-route me-2"></i>故事线设定</h6>
                        <div class="step-controls">
                            <button class="btn btn-outline-primary btn-sm" onclick="toggleEditMode('storyline_generation')">
                                <i class="fas fa-edit me-1"></i>编辑
                            </button>
                            <button class="btn btn-outline-info btn-sm" onclick="assessQuality('storyline_generation')">
                                <i class="fas fa-star me-1"></i>质量评估
                            </button>
                            <button class="btn btn-outline-success btn-sm" onclick="optimizeStorylineBasedOnQuality()">
                                <i class="fas fa-magic me-1"></i>基于质量评估优化
                            </button>
                        </div>
                    </div>
                    
                    ${Utils.generateQualityAssessmentHTML(qualityAssessment, false)}
                    
                    <div class="storyline-details" id="storyline-content">
                        <div class="storyline-section mb-3">
                            <h6 class="text-primary">主要目标</h6>
                            <p><span class="editable" data-field="overall_storyline.main_goal">${storyline.overall_storyline?.main_goal || '未知'}</span></p>
                        </div>
                        
                        <div class="storyline-section mb-3">
                            <h6 class="text-primary">主要冲突</h6>
                            <div class="conflict-details">
                                <div class="mb-2">
                                    <strong>外部冲突:</strong> <span class="editable" data-field="overall_storyline.core_conflict.external">${storyline.overall_storyline?.core_conflict?.external || '未知'}</span>
                                </div>
                                <div class="mb-2">
                                    <strong>内部冲突:</strong> <span class="editable" data-field="overall_storyline.core_conflict.internal">${storyline.overall_storyline?.core_conflict?.internal || '未知'}</span>
                                </div>
                                <div class="mb-2">
                                    <strong>人际冲突:</strong> <span class="editable" data-field="overall_storyline.core_conflict.interpersonal">${storyline.overall_storyline?.core_conflict?.interpersonal || '未知'}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="storyline-section mb-3">
                            <h6 class="text-primary">世界观设定</h6>
                            <div class="world-setting-details">
                                <div class="mb-2">
                                    <strong>时代背景:</strong> <span class="editable" data-field="overall_storyline.world_setting.time_period">${storyline.overall_storyline?.world_setting?.time_period || '未知'}</span>
                                </div>
                                <div class="mb-2">
                                    <strong>地点设定:</strong> <span class="editable" data-field="overall_storyline.world_setting.location">${storyline.overall_storyline?.world_setting?.location || '未知'}</span>
                                </div>
                                <div class="mb-2">
                                    <strong>社会背景:</strong> <span class="editable" data-field="overall_storyline.world_setting.society">${storyline.overall_storyline?.world_setting?.society || '未知'}</span>
                                </div>
                                <div class="mb-2">
                                    <strong>氛围基调:</strong> <span class="editable" data-field="overall_storyline.world_setting.atmosphere">${storyline.overall_storyline?.world_setting?.atmosphere || '未知'}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="storyline-section mb-3">
                            <h6 class="text-primary">故事主题</h6>
                            <p><span class="editable" data-field="overall_storyline.themes" title="编辑提示：多个主题用逗号分隔，如：成长,爱情,冒险">${Array.isArray(storyline.overall_storyline?.themes) ? storyline.overall_storyline.themes.join(', ') : (storyline.overall_storyline?.themes || '未知')}</span></p>
                        </div>
                        
                        <div class="storyline-section mb-3">
                            <h6 class="text-primary">故事基调</h6>
                            <p><span class="editable" data-field="overall_storyline.tone">${storyline.overall_storyline?.tone || '未知'}</span></p>
                        </div>
                        
                        <div class="storyline-section mb-3">
                            <h6 class="text-primary">目标受众</h6>
                            <p><span class="editable" data-field="overall_storyline.target_audience">${storyline.overall_storyline?.target_audience || '未知'}</span></p>
                        </div>
                        
                        <div class="storyline-section mb-3">
                            <h6 class="text-primary">商业潜力</h6>
                            <p><span class="editable" data-field="overall_storyline.commercial_potential">${storyline.overall_storyline?.commercial_potential || '未知'}</span></p>
                        </div>
                    </div>
                    
                    <div class="step-actions mt-3">
                        <button class="btn btn-warning btn-sm" onclick="regenerateStep('storyline_generation')">
                            <i class="fas fa-redo me-2"></i>重新生成故事线
                        </button>
                        <button class="btn btn-info btn-sm" onclick="improveStep('storyline_generation')">
                            <i class="fas fa-magic me-2"></i>改进故事线
                        </button>
                        <button class="btn btn-success btn-sm" onclick="saveStepContent('storyline_generation')" style="display: none;" id="save-storyline-generation-btn">
                            <i class="fas fa-save me-2"></i>保存修改
                        </button>
                    </div>
                </div>
            `;
        }
    },
    
    // 加载知识图谱详情
    loadKnowledgeGraphDetails: async (contentElement) => {
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/knowledge_graph`);
        
        if (response.success) {
            const kg = response.data;
            contentElement.innerHTML = `
                <div class="step-detail-content">
                    <h6><i class="fas fa-project-diagram me-2"></i>知识图谱</h6>
                    
                    <div class="knowledge-graph-details">
                        <div class="kg-section mb-3">
                            <h6 class="text-primary">实体 (${kg.entities?.length || 0}个)</h6>
                            <div class="entities-list">
                                ${(kg.entities || []).map(entity => `
                                    <div class="entity-item">
                                        <strong>${entity.id}</strong> (${entity.type})
                                        ${entity.attributes ? `
                                            <div class="entity-attributes">
                                                ${Object.entries(entity.attributes).map(([key, value]) => 
                                                    `<small>${key}: ${value}</small>`
                                                ).join(' | ')}
                                            </div>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        
                        <div class="kg-section mb-3">
                            <h6 class="text-primary">关系 (${kg.relations?.length || 0}个)</h6>
                            <div class="relations-list">
                                ${(kg.relations || []).map(relation => `
                                    <div class="relation-item">
                                        <strong>${relation.source}</strong> 
                                        <span class="relation-type">${relation.relation_type}</span> 
                                        <strong>${relation.target}</strong>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                    
                    <div class="step-actions mt-3">
                        <button class="btn btn-warning btn-sm" onclick="regenerateStep('knowledge_graph_creation')">
                            <i class="fas fa-redo me-2"></i>重新生成知识图谱
                        </button>
                    </div>
                </div>
            `;
        }
    },
    
    // 加载章节详情
    loadChapterDetails: async (contentElement) => {
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/chapters`);
        
        if (response.success) {
            const chapters = response.data;
            const firstChapter = chapters[0];
            
            if (firstChapter) {
                contentElement.innerHTML = `
                    <div class="step-detail-content">
                        <h6><i class="fas fa-pen-fancy me-2"></i>第一章内容</h6>
                        
                        <div class="chapter-details">
                            <div class="chapter-header mb-3">
                                <h5 class="chapter-title">${firstChapter.title || '第一章'}</h5>
                                <div class="chapter-meta">
                                    <span class="badge bg-primary">字数: ${firstChapter.content?.length || 0}</span>
                                </div>
                            </div>
                            
                            <div class="chapter-content">
                                <div class="chapter-text" style="max-height: 300px; overflow-y: auto; border: 1px solid #e9ecef; padding: 15px; border-radius: 5px; background-color: #f8f9fa;">
                                    ${Utils.formatChapterContent((firstChapter.content || '').substring(0, 1500))}${(firstChapter.content || '').length > 1500 ? '...' : ''}
                                </div>
                            </div>
                            
                            <div class="chapter-actions mt-3">
                                <button class="btn btn-primary btn-sm" onclick="viewFullChapter('${firstChapter.chapter_number}')">
                                    <i class="fas fa-eye me-2"></i>查看完整章节
                                </button>
                                <button class="btn btn-warning btn-sm" onclick="regenerateStep('chapter_writing')">
                                    <i class="fas fa-redo me-2"></i>重新生成章节
                                </button>
                                <button class="btn btn-success btn-sm" onclick="downloadChapter('${firstChapter.chapter_number}')">
                                    <i class="fas fa-download me-2"></i>下载章节
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }
        }
    },
    
    // 续写相关详情加载函数
    loadContinuationStorylineDetails: async (contentElement) => {
        try {
            const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation-status`);
            if (response.success && response.data.continuation_state) {
                const storyline = response.data.continuation_state.next_chapter_storyline;
                if (storyline) {
                    // 获取质量评估数据
                    let qualityAssessment = null;
                    try {
                        const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/continuation_storyline_quality_assessment`);
                        if (qualityResponse.success) {
                            qualityAssessment = qualityResponse.data;
                        }
                    } catch (error) {
                        console.log('未找到续写故事线质量评估数据');
                    }
                    contentElement.innerHTML = `
                        <div class="step-detail-content">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h6><i class="fas fa-route me-2"></i>续写故事线详情</h6>
                                <div class="step-controls">
                                    <button class="btn btn-outline-primary btn-sm" onclick="toggleContinuationEditMode('continuation_storyline')">
                                        <i class="fas fa-edit me-1"></i>编辑
                                    </button>
                                    <button class="btn btn-outline-info btn-sm" onclick="assessContinuationQuality('storyline')">
                                        <i class="fas fa-star me-1"></i>质量评估
                                    </button>
                                    <button class="btn btn-outline-success btn-sm" onclick="optimizeContinuationStorylineBasedOnQuality()">
                                        <i class="fas fa-magic me-1"></i>基于质量评估优化
                                    </button>
                                </div>
                            </div>
                            
                            <div class="storyline-details">
                                <div class="storyline-actions mb-3" style="display: none;">
                                    <button class="btn btn-outline-info btn-sm" onclick="assessContinuationQuality('storyline')">
                                        <i class="fas fa-star me-1"></i>质量评估
                                    </button>
                                    <button class="btn btn-outline-success btn-sm" onclick="optimizeContinuationStorylineBasedOnQuality()">
                                        <i class="fas fa-magic me-1"></i>基于质量评估优化
                                    </button>
                                </div>
                                
                                ${Utils.generateQualityAssessmentHTML(qualityAssessment, false)}
                                
                                <div class="storyline-section mb-3">
                                    <h6 class="text-primary">章节信息</h6>
                                    <p><strong>章节号：</strong><span class="editable" data-field="chapter_number">${storyline.chapter_number || '未知'}</span></p>
                                    <p><strong>章节标题：</strong><span class="editable" data-field="chapter_title">${storyline.chapter_title || '未知'}</span></p>
                                </div>
                                
                                <div class="storyline-section mb-3">
                                    <h6 class="text-primary">场景设定</h6>
                                    <p><strong>时间：</strong><span class="editable" data-field="scene_setting.time">${storyline.scene_setting?.time || '未知'}</span></p>
                                    <p><strong>地点：</strong><span class="editable" data-field="scene_setting.location">${storyline.scene_setting?.location || '未知'}</span></p>
                                    <p><strong>氛围：</strong><span class="editable" data-field="scene_setting.atmosphere">${storyline.scene_setting?.atmosphere || '未知'}</span></p>
                                    <p><strong>天气：</strong><span class="editable" data-field="scene_setting.weather">${storyline.scene_setting?.weather || '未知'}</span></p>
                                </div>
                                
                                <div class="storyline-section mb-3">
                                    <h6 class="text-primary">情节要点</h6>
                                    <div class="editable" data-field="plot_points">
                                        <ul>
                                            ${(storyline.plot_points || []).map(point => `<li>${point}</li>`).join('')}
                                        </ul>
                                    </div>
                                </div>
                                
                                <div class="storyline-section mb-3">
                                    <h6 class="text-primary">关键事件</h6>
                                    <div class="editable" data-field="key_events">
                                        <ul>
                                            ${(storyline.key_events || []).map(event => `<li>${event}</li>`).join('')}
                                        </ul>
                                    </div>
                                </div>
                                
                                <div class="storyline-section mb-3">
                                    <h6 class="text-primary">伏笔设置</h6>
                                    <div class="editable" data-field="foreshadowing">
                                        <ul>
                                            ${(storyline.foreshadowing || []).map(hint => `<li>${hint}</li>`).join('')}
                                        </ul>
                                    </div>
                                </div>
                                
                                <div class="storyline-section mb-3">
                                    <h6 class="text-primary">章节结尾</h6>
                                    <p class="editable" data-field="chapter_ending">${storyline.chapter_ending || '未知'}</p>
                                </div>
                                
                                <div class="storyline-section mb-3">
                                    <h6 class="text-primary">下章预告</h6>
                                    <p class="editable" data-field="next_chapter_hint">${storyline.next_chapter_hint || '未知'}</p>
                                </div>
                                
                                <div class="step-actions mt-4">
                                    <button class="btn btn-warning btn-sm" onclick="regenerateContinuationStep('storyline_generation')">
                                        <i class="fas fa-redo me-2"></i>重新生成故事线
                                    </button>
                                    <button class="btn btn-info btn-sm" onclick="improveContinuationStep('storyline_generation')">
                                        <i class="fas fa-magic me-2"></i>改进故事线
                                    </button>
                                    <button id="save-continuation-storyline-btn" class="btn btn-success btn-sm" style="display: none;" onclick="saveContinuationStorylineContent()">
                                        <i class="fas fa-save me-2"></i>保存修改
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    contentElement.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            暂无续写故事线数据
                        </div>
                    `;
                }
            }
        } catch (error) {
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    加载续写故事线详情失败: ${error.message}
                </div>
            `;
        }
    },
    
    loadContinuationStorylineImprovementDetails: async (contentElement) => {
        contentElement.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                故事线优化详情功能开发中...
            </div>
        `;
    },
    
    loadContinuationQualityAssessmentDetails: async (contentElement) => {
        try {
            // 尝试获取续写故事线质量评估数据
            const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/continuation_storyline_quality_assessment`);
            
            if (qualityResponse.success) {
                const quality = qualityResponse.data;
                
                contentElement.innerHTML = `
                    <div class="step-detail-content">
                        <h6><i class="fas fa-clipboard-check me-2"></i>续写故事线质量评估</h6>
                        
                        <div class="quality-summary mb-3">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="quality-metric">
                                        <span class="metric-label">总体评分:</span>
                                        <span class="metric-value score-${quality.quality_level || 'medium'}">${quality.overall_score || '未知'}</span>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="quality-metric">
                                        <span class="metric-label">质量等级:</span>
                                        <span class="quality-badge quality-${quality.quality_level || 'medium'}">${quality.quality_level || '未知'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${quality.suggestions && quality.suggestions.length > 0 ? `
                        <div class="quality-suggestions mb-3">
                            <h6><i class="fas fa-lightbulb me-2"></i>改进建议</h6>
                            <ul class="list-unstyled">
                                ${quality.suggestions.map(suggestion => `
                                    <li><i class="fas fa-arrow-right me-2 text-primary"></i>${suggestion}</li>
                                `).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        
                        <div class="quality-actions">
                            <button class="btn btn-primary btn-sm me-2" onclick="assessContinuationQuality('storyline')">
                                <i class="fas fa-redo me-1"></i>重新评估
                            </button>
                            ${quality.overall_score < 60 ? `
                            <button class="btn btn-warning btn-sm" onclick="optimizeContinuationStorylineBasedOnQuality()">
                                <i class="fas fa-magic me-1"></i>智能优化
                            </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            } else {
                contentElement.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        暂无质量评估数据，请先生成续写故事线
                        <div class="mt-2">
                            <button class="btn btn-primary btn-sm" onclick="assessContinuationQuality('storyline')">
                                <i class="fas fa-clipboard-check me-1"></i>开始质量评估
                            </button>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    加载质量评估数据失败: ${error.message}
                </div>
            `;
        }
    },
    
    loadContinuationChapterDetails: async (contentElement) => {
        try {
            // 优先从已保存的章节文件中获取数据（历史记录）
            let chapter = null;
            const chaptersResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/chapters`);
            if (chaptersResponse.success && chaptersResponse.data.length > 0) {
                // 获取最新的章节（续写章节）
                chapter = chaptersResponse.data[chaptersResponse.data.length - 1];
            }
            
            // 如果已保存的章节中没有数据，再尝试从缓存中获取
            if (!chapter) {
                const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation-status`);
                if (response.success && response.data.continuation_state) {
                    chapter = response.data.continuation_state.next_chapter_content;
                }
            }
            
            if (chapter) {
                    
                    // 获取质量评估数据
                    let qualityAssessment = null;
                    try {
                        const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/continuation_chapter_quality_assessment`);
                        if (qualityResponse.success) {
                            qualityAssessment = qualityResponse.data;
                            console.log('质量评估数据:', qualityAssessment);
                        }
                    } catch (error) {
                        console.log('未找到续写章节质量评估数据，这是正常的，因为还没有进行质量评估');
                    }
                    
                    // 检查是否有解析错误
                    if (chapter.parse_error) {
                        contentElement.innerHTML = `
                            <div class="step-detail-content">
                                <h6><i class="fas fa-pen-fancy me-2"></i>续写章节详情</h6>
                                
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle me-2"></i>
                                    <strong>章节生成出现问题</strong><br>
                                    章节内容生成时遇到技术问题，可能是由于网络超时或API限制导致的。
                                </div>
                                
                                <div class="chapter-actions mb-3">
                                    <button class="btn btn-warning btn-sm" onclick="regenerateContinuationStep('chapter_writing')">
                                        <i class="fas fa-redo me-2"></i>重新生成章节
                                    </button>
                                    <button class="btn btn-outline-secondary btn-sm" onclick="clearContinuationChapterCache()">
                                        <i class="fas fa-trash me-2"></i>清除错误数据
                                    </button>
                                </div>
                                
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle me-2"></i>
                                    <strong>建议操作：</strong><br>
                                    1. 点击"重新生成章节"按钮重新生成内容<br>
                                    2. 如果问题持续，可以点击"清除错误数据"后重新开始
                                </div>
                            </div>
                        `;
                    } else {
                        contentElement.innerHTML = `
                            <div class="step-detail-content">
                                <h6><i class="fas fa-pen-fancy me-2"></i>续写章节详情</h6>
                                
                                <div class="chapter-actions mb-3">
                                    <button class="btn btn-outline-info btn-sm" onclick="assessContinuationQuality('story')">
                                        <i class="fas fa-star me-1"></i>质量评估
                                    </button>
                                    <button class="btn btn-warning btn-sm" onclick="regenerateContinuationStep('chapter_writing')">
                                        <i class="fas fa-redo me-2"></i>重新生成章节
                                    </button>
                                </div>
                                
                                <div class="chapter-details">
                                    ${qualityAssessment ? `
                                        <div class="quality-assessment mb-3">
                                            <div class="quality-score ${qualityAssessment.overall_score >= 80 ? 'high' : qualityAssessment.overall_score >= 60 ? 'medium' : 'low'}">
                                                <i class="fas fa-star me-2"></i>
                                                质量评分: ${qualityAssessment.overall_score}分
                                            </div>
                                            ${qualityAssessment.suggestions && qualityAssessment.suggestions.length > 0 ? `
                                                <div class="quality-suggestions mt-2">
                                                    <h6 class="text-warning">改进建议:</h6>
                                                    <ul class="suggestions-list">
                                                        ${qualityAssessment.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                                                    </ul>
                                                </div>
                                            ` : ''}
                                        </div>
                                    ` : ''}
                                    
                                    <div class="chapter-section mb-3">
                                        <h6 class="text-primary">章节信息</h6>
                                        <p><strong>标题：</strong>${chapter.title || '未知'}</p>
                                        <p><strong>字数：</strong>${chapter.word_count || (chapter.content ? chapter.content.length : 0) || '未知'}</p>
                                    </div>
                                    
                                    <div class="chapter-section mb-3">
                                        <h6 class="text-primary">章节概要</h6>
                                        <p class="${chapter.summary && !chapter.summary.includes('待') ? '' : 'text-muted'}">
                                            ${chapter.summary || '章节概要待生成'}
                                        </p>
                                    </div>
                                    
                                    <div class="chapter-section mb-3">
                                        <h6 class="text-primary">关键事件</h6>
                                        <ul>
                                            ${(chapter.key_events || []).length > 0 ? 
                                                (chapter.key_events || []).map(event => `<li>${event}</li>`).join('') :
                                                '<li class="text-muted">关键事件待提取</li>'
                                            }
                                        </ul>
                                    </div>
                                    
                                    <div class="chapter-section mb-3">
                                        <h6 class="text-primary">人物发展</h6>
                                        <p class="${chapter.character_development && !chapter.character_development.includes('待') ? '' : 'text-muted'}">
                                            ${chapter.character_development || '人物发展待描述'}
                                        </p>
                                    </div>
                                    
                                    <div class="chapter-section mb-3">
                                        <h6 class="text-primary">伏笔设置</h6>
                                        <ul>
                                            ${(chapter.foreshadowing || []).length > 0 ? 
                                                (chapter.foreshadowing || []).map(hint => `<li>${hint}</li>`).join('') :
                                                '<li class="text-muted">伏笔设置待分析</li>'
                                            }
                                        </ul>
                                    </div>
                                    
                                    <div class="chapter-section mb-3">
                                        <h6 class="text-primary">下章预告</h6>
                                        <p class="${chapter.next_chapter_hint && !chapter.next_chapter_hint.includes('待') ? '' : 'text-muted'}">
                                            ${chapter.next_chapter_hint || '下章预告待生成'}
                                        </p>
                                    </div>
                                    
                                    <div class="chapter-section mb-3">
                                        <h6 class="text-primary">章节内容预览</h6>
                                        <div class="chapter-text" style="max-height: 300px; overflow-y: auto; border: 1px solid #e9ecef; padding: 15px; border-radius: 5px; background-color: #f8f9fa;">
                                            ${Utils.formatChapterContent((chapter.content || '').substring(0, 1500))}${(chapter.content || '').length > 1500 ? '...' : ''}
                                        </div>
                                        <button class="btn btn-outline-primary btn-sm mt-2" onclick="showContinuationChapterModal('${AppState.currentNovelId}')">
                                            <i class="fas fa-eye me-1"></i>查看完整内容
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `;
                    }
                } else {
                    contentElement.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            暂无续写章节数据
                        </div>
                    `;
                }
        } catch (error) {
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    加载续写章节详情失败: ${error.message}
                </div>
            `;
        }
    },
    
    loadContinuationChapterQualityDetails: async (contentElement) => {
        try {
            // 尝试获取续写章节质量评估数据
            const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/continuation_chapter_quality_assessment`);
            
            if (qualityResponse.success) {
                const quality = qualityResponse.data;
                
                contentElement.innerHTML = `
                    <div class="step-detail-content">
                        <h6><i class="fas fa-clipboard-check me-2"></i>续写章节质量评估</h6>
                        
                        <div class="quality-summary mb-3">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="quality-metric">
                                        <span class="metric-label">总体评分:</span>
                                        <span class="metric-value score-${quality.quality_level || 'medium'}">${quality.overall_score || '未知'}</span>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="quality-metric">
                                        <span class="metric-label">质量等级:</span>
                                        <span class="quality-badge quality-${quality.quality_level || 'medium'}">${quality.quality_level || '未知'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${quality.suggestions && quality.suggestions.length > 0 ? `
                        <div class="quality-suggestions mb-3">
                            <h6><i class="fas fa-lightbulb me-2"></i>改进建议</h6>
                            <ul class="list-unstyled">
                                ${quality.suggestions.map(suggestion => `
                                    <li><i class="fas fa-arrow-right me-2 text-primary"></i>${suggestion}</li>
                                `).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        
                        <div class="quality-actions">
                            <button class="btn btn-primary btn-sm me-2" onclick="assessContinuationQuality('story')">
                                <i class="fas fa-redo me-1"></i>重新评估
                            </button>
                            ${quality.overall_score < 60 ? `
                            <button class="btn btn-warning btn-sm" onclick="improveContinuationStep('chapter_writing')">
                                <i class="fas fa-magic me-1"></i>智能优化
                            </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            } else {
                contentElement.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        暂无章节质量评估数据，请先写作续写章节
                        <div class="mt-2">
                            <button class="btn btn-primary btn-sm" onclick="assessContinuationQuality('story')">
                                <i class="fas fa-clipboard-check me-1"></i>开始质量评估
                            </button>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    加载章节质量评估数据失败: ${error.message}
                </div>
            `;
        }
    },
    
    loadContinuationChapterSaveDetails: async (contentElement) => {
        try {
            // 获取已保存的章节列表
            const chaptersResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/chapters`);
            
            if (chaptersResponse.success && chaptersResponse.data.length > 0) {
                const chapters = chaptersResponse.data;
                const latestChapter = chapters[chapters.length - 1];
                
                contentElement.innerHTML = `
                    <div class="step-detail-content">
                        <h6><i class="fas fa-save me-2"></i>续写章节保存状态</h6>
                        
                        <div class="save-status mb-3">
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle me-2"></i>
                                最新章节已成功保存
                            </div>
                        </div>
                        
                        <div class="chapter-info mb-3">
                            <div class="row">
                                <div class="col-md-4">
                                    <div class="info-item">
                                        <span class="info-label">章节编号:</span>
                                        <span class="info-value">第 ${latestChapter.chapter_number || '未知'} 章</span>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="info-item">
                                        <span class="info-label">字数统计:</span>
                                        <span class="info-value">${latestChapter.word_count || 0} 字</span>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="info-item">
                                        <span class="info-label">保存时间:</span>
                                        <span class="info-value">${Utils.formatDate(latestChapter.created_at)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${latestChapter.title ? `
                        <div class="chapter-title mb-3">
                            <h6><i class="fas fa-heading me-2"></i>章节标题</h6>
                            <p class="chapter-title-text">${latestChapter.title}</p>
                        </div>
                        ` : ''}
                        
                        <div class="save-actions">
                            <button class="btn btn-outline-primary btn-sm me-2" onclick="window.location.reload()">
                                <i class="fas fa-sync-alt me-1"></i>刷新状态
                            </button>
                            <button class="btn btn-success btn-sm" onclick="startNextChapter()">
                                <i class="fas fa-plus me-1"></i>开始下一章
                            </button>
                        </div>
                    </div>
                `;
            } else {
                contentElement.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        暂无已保存的续写章节数据
                        <div class="mt-2">
                            <button class="btn btn-primary btn-sm" onclick="executeContinuationStep('chapter_writing')">
                                <i class="fas fa-pen me-1"></i>开始写作章节
                            </button>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    加载章节保存状态失败: ${error.message}
                </div>
            `;
        }
    },
    
    // 加载续写内容改进详情
    loadContinuationContentImprovementDetails: async (contentElement) => {
        try {
            // 获取续写章节内容
            const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation-status`);
            
            if (response.success && response.data.continuation_state) {
                const chapterContent = response.data.continuation_state.next_chapter_content;
                
                if (chapterContent) {
                    contentElement.innerHTML = `
                        <div class="step-detail-content">
                            <h6><i class="fas fa-edit me-2"></i>续写内容改进</h6>
                            
                            <div class="improvement-info mb-3">
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle me-2"></i>
                                    基于质量评估结果对章节内容进行智能优化
                                </div>
                            </div>
                            
                            <div class="chapter-preview mb-3">
                                <h6><i class="fas fa-eye me-2"></i>当前章节内容预览</h6>
                                <div class="content-preview">
                                    <p class="text-muted">${(chapterContent.content || '').substring(0, 200)}${(chapterContent.content || '').length > 200 ? '...' : ''}</p>
                                </div>
                            </div>
                            
                            <div class="improvement-actions">
                                <button class="btn btn-primary btn-sm me-2" onclick="improveContinuationStep('chapter_writing')">
                                    <i class="fas fa-magic me-1"></i>开始改进
                                </button>
                                <button class="btn btn-outline-secondary btn-sm" onclick="executeContinuationStep('chapter_save')">
                                    <i class="fas fa-forward me-1"></i>跳过改进
                                </button>
                            </div>
                        </div>
                    `;
                } else {
                    contentElement.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            暂无章节内容，请先完成章节写作
                            <div class="mt-2">
                                <button class="btn btn-primary btn-sm" onclick="executeContinuationStep('chapter_writing')">
                                    <i class="fas fa-pen me-1"></i>开始写作章节
                                </button>
                            </div>
                        </div>
                    `;
                }
            } else {
                contentElement.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        无法获取章节内容数据
                    </div>
                `;
            }
        } catch (error) {
            contentElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    加载内容改进详情失败: ${error.message}
                </div>
            `;
        }
    }
};

// 全局函数（供HTML调用）
window.showWelcome = Navigation.showWelcome;
window.showCreateNovel = Navigation.showCreateNovel;
window.showContinueNovel = Navigation.showContinueNovel;
window.showNovelList = Navigation.showNovelList;

// 重置小说选择
window.resetNovelSelection = () => {
    // 重置选择状态
    AppState.selectedNovelId = null;
    
    // 隐藏续写需求表单
    const continuationForm = document.getElementById('continuation-form');
    if (continuationForm) {
        continuationForm.style.display = 'none';
    }
    
    // 恢复小说选择列表的原始HTML结构
    const novelSelection = document.getElementById('novel-selection');
    if (novelSelection) {
        novelSelection.innerHTML = `
            <div class="mb-3">
                <label class="form-label">选择要续写的小说</label>
                <div id="novel-list" class="list-group">
                    <!-- 小说列表将在这里动态加载 -->
                </div>
            </div>
        `;
        novelSelection.style.display = 'block';
    }
    
    // 清空续写需求输入框
    const requirementsInput = document.getElementById('continuation-requirements');
    if (requirementsInput) {
        requirementsInput.value = '';
    }
    
    // 重新加载小说列表
    NovelManager.loadContinuationNovelList();
};

// 显示小说详情用于续写选择
const showNovelDetailForContinuation = (novel, chapters) => {
    const container = document.getElementById('novel-selection');
    
    const detailHtml = `
        <div class="novel-detail-for-continuation">
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-light">
                    <h5 class="mb-0">
                        <i class="fas fa-book me-2"></i>
                        ${novel.title || '未命名小说'}
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="novel-info">
                                <h6 class="text-primary">基本信息</h6>
                                <p><strong>标题:</strong> ${novel.title || '未命名'}</p>
                                <p><strong>状态:</strong> <span class="badge bg-${novel.status === 'completed' ? 'success' : 'warning'}">${novel.status || '未知'}</span></p>
                                <p><strong>创建时间:</strong> ${Utils.formatDate(novel.created_at)}</p>
                                <p><strong>更新时间:</strong> ${Utils.formatDate(novel.updated_at)}</p>
                                <p><strong>章节数:</strong> ${chapters.length}</p>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="novel-stats">
                                <h6 class="text-primary">统计信息</h6>
                                <div class="row text-center">
                                    <div class="col-6">
                                        <div class="stat-item">
                                            <h4 class="text-primary">${chapters.length}</h4>
                                            <small class="text-muted">已写章节</small>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="stat-item">
                                            <h4 class="text-success">${chapters.reduce((total, ch) => total + (ch.word_count || 0), 0)}</h4>
                                            <small class="text-muted">总字数</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    ${chapters.length > 0 ? `
                        <div class="mt-4">
                            <h6 class="text-primary">已有章节</h6>
                            <div class="chapters-preview" id="chapters-preview-${AppState.selectedNovelId}">
                                ${chapters.slice(-3).map(chapter => `
                                    <div class="chapter-preview-item d-flex justify-content-between align-items-center p-2 border rounded mb-2">
                                        <div>
                                            <strong>${chapter.title || `第${chapter.chapter_number}章`}</strong>
                                            <small class="text-muted ms-2">${Utils.formatDate(chapter.created_at)}</small>
                                            <span class="badge bg-secondary ms-2">${chapter.word_count || 0}字</span>
                                        </div>
                                        <button class="btn btn-sm btn-outline-primary" onclick="viewChapterInModal('${AppState.selectedNovelId}', ${chapter.chapter_number})" title="查看章节内容">
                                            <i class="fas fa-eye"></i>
                                        </button>
                                    </div>
                                `).join('')}
                                ${chapters.length > 3 ? `
                                    <div class="text-center mt-2">
                                        <button class="btn btn-sm btn-outline-secondary" onclick="toggleAllChapters('${AppState.selectedNovelId}', ${chapters.length})" id="toggle-chapters-btn-${AppState.selectedNovelId}">
                                            <i class="fas fa-chevron-down me-1"></i>还有 ${chapters.length - 3} 个章节...
                                        </button>
                                    </div>
                                    <div class="all-chapters" id="all-chapters-${AppState.selectedNovelId}" style="display: none;">
                                        ${chapters.slice(0, -3).map(chapter => `
                                            <div class="chapter-preview-item d-flex justify-content-between align-items-center p-2 border rounded mb-2">
                                                <div>
                                                    <strong>${chapter.title || `第${chapter.chapter_number}章`}</strong>
                                                    <small class="text-muted ms-2">${Utils.formatDate(chapter.created_at)}</small>
                                                    <span class="badge bg-secondary ms-2">${chapter.word_count || 0}字</span>
                                                </div>
                                                <button class="btn btn-sm btn-outline-primary" onclick="viewChapterInModal('${AppState.selectedNovelId}', ${chapter.chapter_number})" title="查看章节内容">
                                                    <i class="fas fa-eye"></i>
                                                </button>
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    ` : `
                        <div class="mt-4">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                这是一部新小说，还没有任何章节。您可以开始创作第一章。
                            </div>
                        </div>
                    `}
                </div>
            </div>
            
            <div class="card border-0 shadow-sm">
                <div class="card-header bg-success text-white">
                    <h5 class="mb-0">
                        <i class="fas fa-edit me-2"></i>选择续写方式
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <div class="continuation-option-card h-100">
                                <div class="card h-100 border-2">
                                    <div class="card-body text-center">
                                        <div class="option-icon mb-3">
                                            <i class="fas fa-plus-circle fa-3x text-primary"></i>
                                        </div>
                                        <h6 class="card-title">写新章节</h6>
                                        <p class="card-text text-muted small">
                                            继续故事发展，创作新的章节内容
                                        </p>
                                        <button class="btn btn-primary" onclick="startNewChapterContinuation()">
                                            <i class="fas fa-play me-2"></i>开始续写
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${chapters.length > 0 ? `
                            <div class="col-md-4">
                                <div class="continuation-option-card h-100">
                                    <div class="card h-100 border-2">
                                        <div class="card-body text-center">
                                            <div class="option-icon mb-3">
                                                <i class="fas fa-edit fa-3x text-warning"></i>
                                            </div>
                                            <h6 class="card-title">修改现有章节</h6>
                                            <p class="card-text text-muted small">
                                                优化或重写已有的章节内容
                                            </p>
                                            <button class="btn btn-warning" onclick="showChapterSelectionForEdit()">
                                                <i class="fas fa-list me-2"></i>选择章节
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        <div class="col-md-4">
                            <div class="continuation-option-card h-100">
                                <div class="card h-100 border-2">
                                    <div class="card-body text-center">
                                        <div class="option-icon mb-3">
                                            <i class="fas fa-magic fa-3x text-info"></i>
                                        </div>
                                        <h6 class="card-title">优化内容</h6>
                                        <p class="card-text text-muted small">
                                            改进人物设定、故事线等基础内容
                                        </p>
                                        <button class="btn btn-info" onclick="startContentOptimization()">
                                            <i class="fas fa-cogs me-2"></i>开始优化
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 快速续写选项 -->
                        <div class="col-md-4">
                            <div class="continuation-option-card h-100">
                                <div class="card h-100 border-2 border-success">
                                    <div class="card-body text-center">
                                        <div class="option-icon mb-3">
                                            <i class="fas fa-bolt fa-3x text-success"></i>
                                        </div>
                                        <h6 class="card-title">快速续写</h6>
                                        <p class="card-text text-muted small">
                                            自动续写多章或持续写作，一键完成完整流程
                                        </p>
                       <button class="btn btn-success" onclick="showQuickContinuationDialog()">
                           <i class="fas fa-rocket me-2"></i>快速续写
                       </button>
                       <button class="btn btn-info btn-sm mt-2" onclick="checkQuickContinuationProgress()">
                           <i class="fas fa-chart-line me-2"></i>查看进度
                       </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mt-4 text-center">
                        <button type="button" class="btn btn-outline-secondary" onclick="resetNovelSelection()">
                            <i class="fas fa-arrow-left me-2"></i>重新选择小说
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = detailHtml;
};

// 开始新章节续写
window.startNewChapterContinuation = () => {
    // 显示续写需求表单
    const continuationForm = document.getElementById('continuation-form');
    if (continuationForm) {
        continuationForm.style.display = 'block';
    }
    
    // 隐藏小说详情
    const novelDetail = document.querySelector('.novel-detail-for-continuation');
    if (novelDetail) {
        novelDetail.style.display = 'none';
    }
};

// 切换显示所有章节
window.toggleAllChapters = (novelId, totalChapters) => {
    const allChaptersDiv = document.getElementById(`all-chapters-${novelId}`);
    const toggleBtn = document.getElementById(`toggle-chapters-btn-${novelId}`);
    
    if (!allChaptersDiv || !toggleBtn) {
        console.error('找不到章节展开/收起元素');
        return;
    }
    
    const isExpanded = allChaptersDiv.style.display !== 'none';
    
    if (isExpanded) {
        // 收起章节
        allChaptersDiv.style.display = 'none';
        toggleBtn.innerHTML = `<i class="fas fa-chevron-down me-1"></i>还有 ${totalChapters - 3} 个章节...`;
        toggleBtn.classList.remove('btn-outline-primary');
        toggleBtn.classList.add('btn-outline-secondary');
    } else {
        // 展开章节
        allChaptersDiv.style.display = 'block';
        toggleBtn.innerHTML = `<i class="fas fa-chevron-up me-1"></i>收起章节`;
        toggleBtn.classList.remove('btn-outline-secondary');
        toggleBtn.classList.add('btn-outline-primary');
    }
};

// 快速续写完成后刷新相关数据
const refreshNovelDataAfterCompletion = async (novelId, chapterNumber = null) => {
    try {
        console.log('开始刷新小说数据...');
        
        // 1. 刷新小说列表
        const novelsResponse = await Utils.apiRequest('/novels');
        if (novelsResponse.success) {
            // 更新AppState中的小说列表
            AppState.novels = novelsResponse.data;
            console.log('小说列表已刷新');
        }
        
        // 2. 如果当前在小说详情页面，刷新章节信息
        const currentPage = document.querySelector('.page.active');
        if (currentPage && currentPage.id === 'novel-selection-page') {
            console.log('当前在小说选择页面，刷新章节信息...');
            
            // 重新加载小说详情
            if (AppState.selectedNovelId === novelId) {
                await loadNovelDetailsForContinuation(novelId);
            }
        }
        
        // 3. 如果当前在续写工作流页面，刷新工作流状态
        if (currentPage && currentPage.id === 'continuation-workflow-page') {
            console.log('当前在续写工作流页面，刷新工作流状态...');
            
            if (AppState.currentNovelId === novelId) {
                await ContinuationManager.loadContinuationWorkflow(novelId);
            }
        }
        
        // 4. 如果当前在快速续写进度页面，刷新进度信息
        if (currentPage && currentPage.id === 'quick-continuation-progress-page') {
            console.log('当前在快速续写进度页面，刷新进度信息...');
            
            if (AppState.currentNovelId === novelId) {
                // 重新加载进度信息
                await QuickContinuationManager.loadProgress(novelId);
            }
        }
        
        // 4. 显示完成提示
        if (chapterNumber) {
            Utils.showMessage(`第${chapterNumber}章续写完成！数据已自动刷新`, 'success');
        } else {
            Utils.showMessage('快速续写完成！数据已自动刷新', 'success');
        }
        
        console.log('小说数据刷新完成');
        
    } catch (error) {
        console.error('刷新小说数据失败:', error);
        Utils.showMessage('快速续写完成，但数据刷新失败，请手动刷新页面', 'warning');
    }
};

// 加载小说详情用于续写选择（刷新用）
const loadNovelDetailsForContinuation = async (novelId) => {
    try {
        // 获取小说元数据
        const metadataResponse = await Utils.apiRequest(`/novels/${novelId}/data/metadata`);
        if (!metadataResponse.success) {
            throw new Error('获取小说元数据失败');
        }
        
        // 获取章节列表
        const chaptersResponse = await Utils.apiRequest(`/novels/${novelId}/chapters`);
        if (!chaptersResponse.success) {
            throw new Error('获取章节列表失败');
        }
        
        const novel = metadataResponse.data;
        const chapters = chaptersResponse.data;
        
        // 重新显示小说详情
        showNovelDetailForContinuation(novel, chapters);
        
    } catch (error) {
        console.error('加载小说详情失败:', error);
        Utils.showMessage('刷新小说详情失败: ' + error.message, 'danger');
    }
};

// 显示章节选择用于编辑
window.showChapterSelectionForEdit = async () => {
    try {
        console.log('showChapterSelectionForEdit 被调用');
        console.log('AppState.selectedNovelId:', AppState.selectedNovelId);
        
        if (!AppState.selectedNovelId) {
            Utils.showMessage('没有选择小说，请重新选择', 'warning');
            return;
        }
        
        Utils.showLoading('正在加载章节列表...');
        
        // 获取章节列表
        const chaptersResponse = await Utils.apiRequest(`/novels/${AppState.selectedNovelId}/chapters`);
        console.log('章节列表响应:', chaptersResponse);
        
        if (!chaptersResponse.success) {
            throw new Error('获取章节列表失败');
        }
        
        const chapters = chaptersResponse.data;
        console.log('章节数据:', chapters);
        
        if (!chapters || chapters.length === 0) {
            Utils.showMessage('该小说还没有章节', 'info');
            return;
        }
        
        // 显示章节选择界面
        displayChapterSelectionForEdit(chapters);
        
    } catch (error) {
        console.error('showChapterSelectionForEdit 错误:', error);
        Utils.showMessage('加载章节列表失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 显示章节选择界面用于编辑
const displayChapterSelectionForEdit = (chapters) => {
    const container = document.getElementById('novel-selection');
    
    const selectionHtml = `
        <div class="chapter-edit-selection">
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-warning text-white">
                    <h5 class="mb-0">
                        <i class="fas fa-edit me-2"></i>
                        选择要修改的章节
                    </h5>
                </div>
                <div class="card-body">
                    <div class="chapters-list">
                        ${chapters.map(chapter => `
                            <div class="chapter-item d-flex justify-content-between align-items-center p-3 border rounded mb-3">
                                <div class="chapter-info">
                                    <h6 class="mb-1">${chapter.title || `第${chapter.chapter_number}章`}</h6>
                                    <div class="chapter-meta">
                                        <span class="badge bg-secondary me-2">${chapter.word_count || 0}字</span>
                                        <small class="text-muted">${Utils.formatDate(chapter.created_at)}</small>
                                    </div>
                                </div>
                                <div class="chapter-actions">
                                    <button class="btn btn-outline-primary btn-sm me-2" onclick="viewChapterInModal('${AppState.selectedNovelId}', ${chapter.chapter_number})" title="查看章节内容">
                                        <i class="fas fa-eye"></i> 查看
                                    </button>
                                    <button class="btn btn-warning btn-sm me-2" onclick="editChapter('${AppState.selectedNovelId}', ${chapter.chapter_number})" title="编辑章节">
                                        <i class="fas fa-edit"></i> 编辑
                                    </button>
                                    <button class="btn btn-danger btn-sm" onclick="deleteChapter('${AppState.selectedNovelId}', ${chapter.chapter_number}, '${chapter.title || `第${chapter.chapter_number}章`}')" title="删除章节">
                                        <i class="fas fa-trash"></i> 删除
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    
                    <div class="mt-4 text-center">
                        <button type="button" class="btn btn-outline-secondary" onclick="selectNovel('${AppState.selectedNovelId}')">
                            <i class="fas fa-arrow-left me-2"></i>返回小说详情
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = selectionHtml;
};

// 编辑章节
window.editChapter = async (novelId, chapterNumber) => {
    try {
        Utils.showMessage('章节编辑功能正在开发中...', 'info');
        // TODO: 实现章节编辑功能
    } catch (error) {
        Utils.showMessage('编辑章节失败: ' + error.message, 'danger');
    }
};

// 开始内容优化
window.startContentOptimization = () => {
    // 切换到创作工作流程页面，让用户优化基础内容
    Navigation.showCreationWorkflow(AppState.selectedNovelId);
};


window.createNovel = async () => {
    const title = document.getElementById('novel-title').value.trim();
    const requirements = document.getElementById('novel-requirements').value.trim();
    
    // 输入验证
    if (!requirements) {
        Utils.showMessage('请输入创作需求', 'warning');
        document.getElementById('novel-requirements').focus();
        return;
    }
    
    if (requirements.length < 10) {
        Utils.showMessage('创作需求至少需要10个字符', 'warning');
        document.getElementById('novel-requirements').focus();
        return;
    }
    
    if (requirements.length > 2000) {
        Utils.showMessage('创作需求不能超过2000个字符', 'warning');
        document.getElementById('novel-requirements').focus();
        return;
    }
    
    if (title && title.length > 100) {
        Utils.showMessage('小说标题不能超过100个字符', 'warning');
        document.getElementById('novel-title').focus();
        return;
    }
    
    // 检查是否包含敏感词（简单检查）
    const sensitiveWords = ['暴力', '色情', '政治'];
    const hasSensitiveWord = sensitiveWords.some(word => requirements.includes(word));
    if (hasSensitiveWord) {
        Utils.showMessage('创作需求包含不当内容，请修改后重试', 'warning');
        return;
    }
    
    await NovelManager.createNovel(title, requirements);
};

window.startContinuation = async () => {
    const requirements = document.getElementById('continuation-requirements').value;
    
    if (!AppState.selectedNovelId) {
        Utils.showMessage('请先选择要续写的小说', 'warning');
        return;
    }
    
    await NovelManager.startContinuation(AppState.selectedNovelId, requirements);
};

window.startContinuationFromList = async (novelId) => {
    AppState.selectedNovelId = novelId;
    await NovelManager.startContinuation(novelId, '');
};

// 开始写下一章
window.startNextChapter = async () => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的续写项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('正在启动下一章续写...');
        
        // 启动下一章续写，默认重置缓存（因为是新的一章）
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation`, {
            method: 'POST',
            body: JSON.stringify({
                user_requirements: '',
                reset_cache: true  // 新的一章需要重置
            })
        });
        
        if (response.success) {
            Utils.showMessage('下一章续写已启动！', 'success');
            // 重新加载续写工作流程
            await ContinuationManager.loadContinuationWorkflow(AppState.currentNovelId);
        }
    } catch (error) {
        Utils.showMessage('启动下一章续写失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

window.executeStep = async (stepName) => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    await WorkflowManager.executeStep(stepName, AppState.currentNovelId);
};

window.executeContinuationStep = async (stepName) => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的续写项目', 'warning');
        return;
    }
    
    await ContinuationManager.executeContinuationStep(stepName, AppState.currentNovelId);
};

window.loadNovelList = NovelManager.loadNovelList;
window.loadCreationWorkflow = WorkflowManager.loadCreationWorkflow;
window.loadContinuationWorkflow = ContinuationManager.loadContinuationWorkflow;

// 步骤详情相关函数
window.toggleStepDetails = StepDetailsManager.toggleStepDetails;

// 重新生成步骤
window.regenerateStep = async (stepKey) => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading(`正在重新生成${stepKey}...`);
        
        // 检查是否在续写模式
        const isContinuationMode = AppState.continuationData && AppState.continuationData.is_continuation;
        
        // 根据步骤类型和模式调用相应的API
        switch (stepKey) {
            case 'tag_selection':
                await Utils.apiRequest(`/novels/${AppState.currentNovelId}/tags`, {
                    method: 'POST'
                });
                break;
            case 'character_creation':
                await Utils.apiRequest(`/novels/${AppState.currentNovelId}/characters`, {
                    method: 'POST'
                });
                break;
            case 'storyline_generation':
                if (isContinuationMode) {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/storyline`, {
                        method: 'POST'
                    });
                } else {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/storyline`, {
                        method: 'POST'
                    });
                }
                break;
            case 'quality_assessment':
                if (isContinuationMode) {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/quality`, {
                        method: 'POST',
                        body: JSON.stringify({ content_type: 'storyline' })
                    });
                }
                break;
            case 'storyline_improvement':
                if (isContinuationMode) {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/storyline/improve`, {
                        method: 'POST'
                    });
                }
                break;
            case 'knowledge_graph_creation':
                await Utils.apiRequest(`/novels/${AppState.currentNovelId}/knowledge-graph`, {
                    method: 'POST'
                });
                break;
            case 'chapter_writing':
                if (isContinuationMode) {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/chapter`, {
                        method: 'POST'
                    });
                } else {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/chapters`, {
                        method: 'POST'
                    });
                }
                break;
            case 'chapter_quality_assessment':
                if (isContinuationMode) {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/quality`, {
                        method: 'POST',
                        body: JSON.stringify({ content_type: 'story' })
                    });
                }
                break;
            case 'content_improvement':
                if (isContinuationMode) {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/chapter/improve`, {
                        method: 'POST',
                        body: JSON.stringify({ suggestions: [] })
                    });
                }
                break;
            case 'chapter_save':
                if (isContinuationMode) {
                    await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/save`, {
                        method: 'POST'
                    });
                }
                break;
            default:
                throw new Error('未知的步骤: ' + stepKey);
        }
        
        Utils.showMessage(`${stepKey}重新生成成功！`, 'success');
        
        // 重新加载工作流程状态
        if (isContinuationMode) {
            await ContinuationManager.loadContinuationWorkflow(AppState.currentNovelId);
        } else {
            await WorkflowManager.loadCreationWorkflow(AppState.currentNovelId);
        }
        
    } catch (error) {
        Utils.showMessage(`重新生成${stepKey}失败: ` + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 改进步骤
window.improveStep = async (stepKey) => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    // 显示改进对话框
    const improvementType = stepKey === 'character_creation' ? 'characters' : 'storyline';
    showImprovementDialog(improvementType);
};

// 显示改进对话框
const showImprovementDialog = (type) => {
    const modalHtml = `
        <div class="modal fade" id="improvementModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-magic me-2"></i>
                            改进${type === 'characters' ? '人物设定' : '故事线'}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label for="improvement-suggestions" class="form-label">
                                改进建议（可选，留空将使用AI自动分析）
                            </label>
                            <textarea class="form-control" id="improvement-suggestions" rows="4" 
                                      placeholder="请输入具体的改进建议，例如：人物性格更加立体，增加内心冲突等"></textarea>
                        </div>
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            如果不填写改进建议，系统将自动分析当前内容并提供改进方案。
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="confirmImprovement('${type}')">
                            <i class="fas fa-magic me-2"></i>开始改进
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除现有模态框
    const existingModal = document.getElementById('improvementModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('improvementModal'));
    modal.show();
};

// 确认改进
window.confirmImprovement = async (type) => {
    const suggestions = document.getElementById('improvement-suggestions').value.trim();
    
    try {
        Utils.showLoading(`正在改进${type}...`);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('improvementModal'));
        modal.hide();
        
        // 调用改进API
        const suggestionsArray = suggestions ? [suggestions] : [];
        await WorkflowManager.improveContent(type, AppState.currentNovelId, suggestionsArray);
        
    } catch (error) {
        Utils.showMessage(`改进${type}失败: ` + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 查看完整章节
window.viewFullChapter = async (chapterNumber) => {
    try {
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/chapters`);
        
        if (response.success) {
            const chapters = response.data;
            const chapter = chapters.find(ch => ch.chapter_number == chapterNumber);
            
            if (chapter) {
                showChapterModal(chapter);
            }
        }
    } catch (error) {
        Utils.showMessage('加载章节失败: ' + error.message, 'danger');
    }
};

// 显示续写章节模态框
window.showContinuationChapterModal = async (novelId) => {
    try {
        Utils.showLoading('正在加载章节内容...');
        
        // 优先从已保存的章节文件中获取数据（历史记录）
        let chapter = null;
        const chaptersResponse = await Utils.apiRequest(`/novels/${novelId}/chapters`);
        if (chaptersResponse.success && chaptersResponse.data.length > 0) {
            // 获取最新的章节（续写章节）
            chapter = chaptersResponse.data[chaptersResponse.data.length - 1];
        }
        
        // 如果已保存的章节中没有数据，再尝试从缓存中获取
        if (!chapter) {
            const continuationResponse = await Utils.apiRequest(`/novels/${novelId}/continuation-status`);
            if (continuationResponse.success && continuationResponse.data.continuation_state) {
                chapter = continuationResponse.data.continuation_state.next_chapter_content;
            }
        }
        
        if (chapter && !chapter.parse_error) {
            showChapterModal(chapter);
        } else {
            Utils.showMessage('章节内容不可用，请重新生成', 'warning');
        }
    } catch (error) {
        Utils.showMessage('加载章节内容失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 显示章节模态框
const showChapterModal = (chapter) => {
    const modalHtml = `
        <div class="modal fade" id="chapterModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-book me-2"></i>
                            ${chapter.title || `第${chapter.chapter_number}章`}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="chapter-content">
                            <div class="chapter-meta mb-3">
                                <span class="badge bg-primary">字数: ${chapter.word_count || 0}</span>
                                <span class="badge bg-secondary ms-2">章节: ${chapter.chapter_number}</span>
                            </div>
                            <div class="chapter-text">
                                ${Utils.formatChapterContent(chapter.content || '')}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-success" onclick="downloadChapter('${chapter.chapter_number}')">
                            <i class="fas fa-download me-2"></i>下载章节
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除现有模态框
    const existingModal = document.getElementById('chapterModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('chapterModal'));
    modal.show();
};

// 下载章节
window.downloadChapter = async (chapterNumber) => {
    try {
        Utils.showLoading('正在准备下载...');
        
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/chapters/${chapterNumber}/txt`, {
            method: 'POST'
        });
        
        if (response.success) {
            Utils.showMessage('章节已保存为TXT文件！', 'success');
        }
    } catch (error) {
        Utils.showMessage('下载章节失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 编辑模式管理
const EditModeManager = {
    currentEditMode: null,
    
    // 切换编辑模式
    toggleEditMode: (stepKey) => {
        if (EditModeManager.currentEditMode === stepKey) {
            // 退出编辑模式
            EditModeManager.exitEditMode();
        } else {
            // 进入编辑模式
            EditModeManager.enterEditMode(stepKey);
        }
    },
    
    // 进入编辑模式
    enterEditMode: (stepKey) => {
        // 如果已经在编辑其他内容，先退出
        if (EditModeManager.currentEditMode && EditModeManager.currentEditMode !== stepKey) {
            EditModeManager.exitEditMode();
        }
        
        EditModeManager.currentEditMode = stepKey;
        
        // 为所有可编辑元素添加编辑功能
        const editableElements = document.querySelectorAll('.editable');
        editableElements.forEach(element => {
            element.contentEditable = true;
            element.classList.add('editing');
            element.addEventListener('blur', EditModeManager.onContentChange);
            element.addEventListener('keydown', EditModeManager.onKeyDown);
        });
        
        // 显示保存按钮
        let saveBtnId;
        if (stepKey === 'character_creation') {
            saveBtnId = 'save-character-creation-btn';
        } else if (stepKey === 'storyline_generation') {
            saveBtnId = 'save-storyline-generation-btn';
        } else {
            saveBtnId = `save-${stepKey.replace('_', '-')}-btn`;
        }
        
        const saveBtn = document.getElementById(saveBtnId);
        if (saveBtn) {
            saveBtn.style.display = 'inline-block';
        }
        
        // 隐藏其他保存按钮
        document.querySelectorAll('[id^="save-"][id$="-btn"]').forEach(btn => {
            if (btn.id !== saveBtnId) {
                btn.style.display = 'none';
            }
        });
        
        Utils.showMessage('已进入编辑模式，点击内容进行修改', 'info');
    },
    
    // 退出编辑模式
    exitEditMode: () => {
        EditModeManager.currentEditMode = null;
        
        // 移除编辑功能
        const editableElements = document.querySelectorAll('.editable');
        editableElements.forEach(element => {
            element.contentEditable = false;
            element.classList.remove('editing');
            element.removeEventListener('blur', EditModeManager.onContentChange);
            element.removeEventListener('keydown', EditModeManager.onKeyDown);
        });
        
        // 隐藏所有保存按钮
        document.querySelectorAll('[id^="save-"][id$="-btn"]').forEach(btn => {
            btn.style.display = 'none';
        });
        
        Utils.showMessage('已退出编辑模式', 'info');
    },
    
    // 内容变化处理
    onContentChange: (event) => {
        const element = event.target;
        element.classList.add('modified');
    },
    
    // 键盘事件处理
    onKeyDown: (event) => {
        // ESC键退出编辑模式
        if (event.key === 'Escape') {
            EditModeManager.exitEditMode();
        }
        // Ctrl+S保存
        if (event.ctrlKey && event.key === 's') {
            event.preventDefault();
            const currentStep = EditModeManager.currentEditMode;
            if (currentStep) {
                ContentSaveManager.saveStepContent(currentStep);
            }
        }
    },
    
    // 获取修改后的内容
    getModifiedContent: () => {
        const modifiedData = {};
        const modifiedElements = document.querySelectorAll('.editable.modified');
        
        modifiedElements.forEach(element => {
            const field = element.getAttribute('data-field');
            const value = element.textContent.trim();
            
            // 解析字段路径
            const fieldParts = field.split('.');
            let current = modifiedData;
            
            for (let i = 0; i < fieldParts.length - 1; i++) {
                const part = fieldParts[i];
                if (!current[part]) {
                    current[part] = {};
                }
                current = current[part];
            }
            
            const lastPart = fieldParts[fieldParts.length - 1];
            
            // 特殊处理数组字段
            if (lastPart === 'personality_traits' || lastPart === 'themes' || lastPart === 'skills' || lastPart === 'distinctive_features') {
                // 如果用户输入的是逗号分隔的字符串，转换为数组
                if (value.includes(',')) {
                    current[lastPart] = value.split(',').map(item => item.trim()).filter(item => item);
                } else if (value) {
                    current[lastPart] = [value];
                } else {
                    current[lastPart] = [];
                }
            } else if (fieldParts.includes('supporting_characters')) {
                // 特殊处理配角字段，保持对象格式
                current[lastPart] = value;
            } else if (lastPart === 'extraversion' || lastPart === 'agreeableness' || lastPart === 'conscientiousness' || lastPart === 'neuroticism' || lastPart === 'openness') {
                // 处理性格评分字段，确保是数字
                const numValue = parseInt(value);
                current[lastPart] = isNaN(numValue) ? 5 : Math.max(1, Math.min(10, numValue));
            } else if (lastPart === 'age') {
                // 处理年龄字段，确保是数字
                const numValue = parseInt(value);
                current[lastPart] = isNaN(numValue) ? 25 : Math.max(1, Math.min(200, numValue));
            } else {
                current[lastPart] = value;
            }
        });
        
        return modifiedData;
    },
    
    // 验证修改内容
    validateModifiedContent: (modifiedData) => {
        const errors = [];
        
        // 检查是否有修改
        if (Object.keys(modifiedData).length === 0) {
            errors.push('没有检测到任何修改');
            return errors;
        }
        
        // 验证角色数据
        if (modifiedData.main_character) {
            const mc = modifiedData.main_character;
            if (mc.basic_info) {
                if (mc.basic_info.name && mc.basic_info.name.length > 50) {
                    errors.push('角色姓名不能超过50个字符');
                }
                if (mc.basic_info.age && (isNaN(mc.basic_info.age) || mc.basic_info.age < 1 || mc.basic_info.age > 200)) {
                    errors.push('角色年龄必须是1-200之间的数字');
                }
            }
        }
        
        return errors;
    }
};

// 质量评估管理
const QualityAssessmentManager = {
    // 执行质量评估
    assessQuality: async (stepKey) => {
        if (!AppState.currentNovelId) {
            Utils.showMessage('没有活跃的小说项目', 'warning');
            return;
        }
        
        try {
            // 先检查是否有未保存的修改
            const modifiedElements = document.querySelectorAll('.editable.modified');
            if (modifiedElements.length > 0) {
                const shouldSave = confirm('检测到未保存的修改，是否先保存修改再进行质量评估？');
                if (shouldSave) {
                    await ContentSaveManager.saveStepContent(stepKey);
                    // 等待保存完成
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }
            
            Utils.showLoading('正在进行质量评估...');
            
            let response;
            if (stepKey === 'character_creation') {
                // 调用人物质量评估API
                response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/characters/quality`, {
                    method: 'POST'
                });
            } else if (stepKey === 'storyline_generation') {
                // 调用故事线质量评估API
                response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/storyline/quality`, {
                    method: 'POST'
                });
            } else {
                throw new Error('不支持的步骤类型: ' + stepKey);
            }
            
            if (response.success) {
                Utils.showMessage('质量评估完成！', 'success');
                // 重新加载步骤详情以显示评估结果
                await StepDetailsManager.loadStepDetails(stepKey);
            }
        } catch (error) {
            console.error('质量评估错误详情:', error);
            Utils.showMessage('质量评估失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 内容保存管理
const ContentSaveManager = {
    // 保存步骤内容
    saveStepContent: async (stepKey) => {
        if (!AppState.currentNovelId) {
            Utils.showMessage('没有活跃的小说项目', 'warning');
            return;
        }
        
        try {
            Utils.showLoading('正在保存修改...');
            
            const modifiedContent = EditModeManager.getModifiedContent();
            
            // 验证修改内容
            const validationErrors = EditModeManager.validateModifiedContent(modifiedContent);
            if (validationErrors.length > 0) {
                Utils.showMessage('保存失败: ' + validationErrors.join(', '), 'warning');
                return;
            }
            
            let response;
            if (stepKey === 'character_creation') {
                // 使用新的智能体改进API
                response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/characters/improve-with-agent`, {
                    method: 'POST',
                    body: JSON.stringify({
                        modifications: modifiedContent
                    })
                });
            } else if (stepKey === 'storyline_generation') {
                response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/storyline`, {
                    method: 'PUT',
                    body: JSON.stringify(modifiedContent)
                });
            } else {
                throw new Error('不支持的步骤类型: ' + stepKey);
            }
            
            if (response.success) {
                let message = '内容保存成功！';
                if (stepKey === 'character_creation' && response.improvement_applied) {
                    message = '人物数据已通过智能体改进并保存！';
                }
                Utils.showMessage(message, 'success');
                EditModeManager.exitEditMode();
                
                // 等待一小段时间确保数据已保存
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // 重新加载步骤详情
                await StepDetailsManager.loadStepDetails(stepKey);
            }
        } catch (error) {
            console.error('保存错误详情:', error);
            Utils.showMessage('保存失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 标签管理
const TagManager = {
    editMode: false,
    modifiedTags: {},
    
    // 切换标签编辑模式
    toggleEditMode: () => {
        TagManager.editMode = !TagManager.editMode;
        
        const removeButtons = document.querySelectorAll('.tag-remove');
        const saveBtn = document.getElementById('save-tags-btn');
        
        if (TagManager.editMode) {
            // 进入编辑模式
            removeButtons.forEach(btn => btn.style.display = 'inline-block');
            if (saveBtn) saveBtn.style.display = 'inline-block';
            Utils.showMessage('已进入标签编辑模式，可以删除标签', 'info');
        } else {
            // 退出编辑模式
            removeButtons.forEach(btn => btn.style.display = 'none');
            if (saveBtn) saveBtn.style.display = 'none';
            Utils.showMessage('已退出标签编辑模式', 'info');
        }
    },
    
    // 删除标签
    removeTag: (category, tag) => {
        const tagElement = document.querySelector(`[data-category="${category}"][data-tag="${tag}"]`);
        if (tagElement) {
            tagElement.remove();
            
            // 记录修改
            if (!TagManager.modifiedTags[category]) {
                TagManager.modifiedTags[category] = [];
            }
            TagManager.modifiedTags[category].push({ action: 'remove', tag: tag });
            
            Utils.showMessage(`已删除标签: ${tag}`, 'success');
        }
    },
    
    // 添加标签
    addTag: (category, tag) => {
        const categoryElement = document.querySelector(`[data-category="${category}"]`);
        if (categoryElement) {
            const tagList = categoryElement.querySelector('.tag-list');
            const newTagElement = document.createElement('span');
            newTagElement.className = 'tag';
            newTagElement.setAttribute('data-category', category);
            newTagElement.setAttribute('data-tag', tag);
            newTagElement.innerHTML = `
                ${tag}
                <i class="fas fa-times tag-remove" onclick="removeTag('${category}', '${tag}')" style="display: ${TagManager.editMode ? 'inline-block' : 'none'};"></i>
            `;
            tagList.appendChild(newTagElement);
            
            // 记录修改
            if (!TagManager.modifiedTags[category]) {
                TagManager.modifiedTags[category] = [];
            }
            TagManager.modifiedTags[category].push({ action: 'add', tag: tag });
            
            Utils.showMessage(`已添加标签: ${tag}`, 'success');
        }
    },
    
    // 获取修改后的标签数据
    getModifiedTags: () => {
        const currentTags = {};
        const tagElements = document.querySelectorAll('.tag');
        
        tagElements.forEach(tagElement => {
            const category = tagElement.getAttribute('data-category');
            const tag = tagElement.getAttribute('data-tag');
            
            if (!currentTags[category]) {
                currentTags[category] = [];
            }
            currentTags[category].push(tag);
        });
        
        return currentTags;
    },
    
    // 保存标签修改
    saveTagChanges: async () => {
        if (!AppState.currentNovelId) {
            Utils.showMessage('没有活跃的小说项目', 'warning');
            return;
        }
        
        try {
            Utils.showLoading('正在保存标签修改...');
            
            const modifiedTags = TagManager.getModifiedTags();
            
            const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/tags`, {
                method: 'PUT',
                body: JSON.stringify({ selected_tags: modifiedTags })
            });
            
            if (response.success) {
                Utils.showMessage('标签修改保存成功！', 'success');
                TagManager.editMode = false;
                TagManager.modifiedTags = {};
                
                // 重新加载标签详情
                await StepDetailsManager.loadStepDetails('tag_selection');
            }
        } catch (error) {
            Utils.showMessage('保存标签修改失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    },
    
    // 显示添加标签模态框
    showAddTagModal: async () => {
        try {
            // 获取可用的标签分类
            const response = await Utils.apiRequest('/config/tags');
            const availableCategories = response.success ? response.data : {};
            
            const modalHtml = `
                <div class="modal fade" id="addTagModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="fas fa-plus me-2"></i>添加标签
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="tag-category" class="form-label">选择标签分类</label>
                                    <select class="form-select" id="tag-category">
                                        ${Object.keys(availableCategories).map(category => 
                                            `<option value="${category}">${category}</option>`
                                        ).join('')}
                                    </select>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="tag-input" class="form-label">输入标签名称</label>
                                    <input type="text" class="form-control" id="tag-input" placeholder="请输入标签名称">
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">或从现有标签中选择</label>
                                    <div id="available-tags">
                                        ${Object.entries(availableCategories).map(([category, tags]) => `
                                            <div class="category-tags mb-2">
                                                <strong>${category}:</strong>
                                                <div class="tag-options">
                                                    ${tags.map(tag => `
                                                        <span class="tag-option" onclick="selectExistingTag('${category}', '${tag}')">${tag}</span>
                                                    `).join('')}
                                                </div>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                                <button type="button" class="btn btn-primary" onclick="confirmAddTag()">
                                    <i class="fas fa-plus me-2"></i>添加标签
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // 移除现有模态框
            const existingModal = document.getElementById('addTagModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // 添加新模态框
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('addTagModal'));
            modal.show();
            
        } catch (error) {
            Utils.showMessage('加载标签选项失败: ' + error.message, 'danger');
        }
    }
};

// 全局函数
window.toggleEditMode = EditModeManager.toggleEditMode;
window.assessQuality = QualityAssessmentManager.assessQuality;
window.saveStepContent = ContentSaveManager.saveStepContent;

// 标签管理全局函数
window.toggleTagEditMode = TagManager.toggleEditMode;
window.removeTag = TagManager.removeTag;
window.showAddTagModal = TagManager.showAddTagModal;
window.saveTagChanges = TagManager.saveTagChanges;

// 选择现有标签
window.selectExistingTag = (category, tag) => {
    document.getElementById('tag-category').value = category;
    document.getElementById('tag-input').value = tag;
};

// 确认添加标签
window.confirmAddTag = () => {
    const category = document.getElementById('tag-category').value;
    const tag = document.getElementById('tag-input').value.trim();
    
    if (!tag) {
        Utils.showMessage('请输入标签名称', 'warning');
        return;
    }
    
    // 检查标签是否已存在
    const existingTag = document.querySelector(`[data-category="${category}"][data-tag="${tag}"]`);
    if (existingTag) {
        Utils.showMessage('该标签已存在', 'warning');
        return;
    }
    
    TagManager.addTag(category, tag);
    
    // 关闭模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('addTagModal'));
    modal.hide();
};

// 小说选择处理
window.selectNovel = async (novelId) => {
    AppState.selectedNovelId = novelId;
    
    try {
        Utils.showLoading('正在加载小说详情...');
        
        // 获取小说基本信息
        const novelResponse = await Utils.apiRequest(`/novels/${novelId}/data/metadata`);
        if (!novelResponse.success) {
            throw new Error('获取小说信息失败');
        }
        
        const novel = novelResponse.data;
        
        // 获取章节列表
        const chaptersResponse = await Utils.apiRequest(`/novels/${novelId}/chapters`);
        const chapters = chaptersResponse.success ? chaptersResponse.data : [];
        
        // 显示小说详情和续写选项
        showNovelDetailForContinuation(novel, chapters);
        
    } catch (error) {
        Utils.showMessage('加载小说详情失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 查看小说详情
window.viewNovelDetails = async (novelId) => {
    try {
        Utils.showLoading('正在加载小说详情...');
        
        // 获取小说基本信息
        const novelResponse = await Utils.apiRequest(`/novels/${novelId}/data/metadata`);
        if (!novelResponse.success) {
            throw new Error('获取小说信息失败');
        }
        
        const novel = novelResponse.data;
        
        // 获取章节列表
        const chaptersResponse = await Utils.apiRequest(`/novels/${novelId}/chapters`);
        const chapters = chaptersResponse.success ? chaptersResponse.data : [];
        
        // 显示详情模态框
        showNovelDetailsModal(novel, chapters);
        
    } catch (error) {
        Utils.showMessage('加载小说详情失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 显示小说详情模态框
const showNovelDetailsModal = (novel, chapters) => {
    const modalHtml = `
        <div class="modal fade" id="novelDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-book me-2"></i>
                            ${novel.title || '未命名小说'}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="novel-info">
                                    <h6 class="text-primary">基本信息</h6>
                                    <p><strong>标题:</strong> ${novel.title || '未命名'}</p>
                                    <p><strong>状态:</strong> <span class="badge bg-${novel.status === 'completed' ? 'success' : 'warning'}">${novel.status || '未知'}</span></p>
                                    <p><strong>创建时间:</strong> ${Utils.formatDate(novel.created_at)}</p>
                                    <p><strong>更新时间:</strong> ${Utils.formatDate(novel.updated_at)}</p>
                                    <p><strong>章节数:</strong> ${chapters.length}</p>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="novel-actions">
                                    <h6 class="text-primary">操作</h6>
                                    <div class="d-grid gap-2">
                                        <button class="btn btn-success" onclick="startContinuationFromList('${novel.novel_id}')">
                                            <i class="fas fa-edit me-2"></i>续写小说
                                        </button>
                                        <button class="btn btn-info" onclick="viewNovelWorkflow('${novel.novel_id}')">
                                            <i class="fas fa-cogs me-2"></i>查看工作流
                                        </button>
                                        <button class="btn btn-warning btn-sm" onclick="checkQuickContinuationProgressForNovel('${novel.novel_id}')">
                                            <i class="fas fa-chart-line me-2"></i>查看续写进度
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        ${chapters.length > 0 ? `
                            <div class="mt-4">
                                <h6 class="text-primary">章节列表</h6>
                                <div class="chapters-list">
                                    ${chapters.map(chapter => `
                                        <div class="chapter-item d-flex justify-content-between align-items-center p-2 border rounded mb-2">
                                            <div>
                                                <strong>${chapter.title || `第${chapter.chapter_number}章`}</strong>
                                                <small class="text-muted ms-2">${Utils.formatDate(chapter.created_at)}</small>
                                            </div>
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="badge bg-secondary">${chapter.word_count || 0}字</span>
                                                <button class="btn btn-sm btn-outline-info" onclick="viewChapterWorkflow('${novel.novel_id}', ${chapter.chapter_number})" title="查看章节工作流">
                                                    <i class="fas fa-cogs me-1"></i>工作流
                                                </button>
                                                <button class="btn btn-sm btn-outline-primary" onclick="viewChapterInModal('${novel.novel_id}', ${chapter.chapter_number})" title="查看章节内容">
                                                    <i class="fas fa-eye"></i>
                                                </button>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除现有模态框
    const existingModal = document.getElementById('novelDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('novelDetailsModal'));
    modal.show();
};

// 查看小说工作流
window.viewNovelWorkflow = (novelId) => {
    // 关闭详情模态框
    const modal = bootstrap.Modal.getInstance(document.getElementById('novelDetailsModal'));
    if (modal) {
        modal.hide();
    }
    
    // 进入创作流程页面
    Navigation.showCreationWorkflow(novelId);
};

// 在模态框中查看章节
window.viewChapterInModal = async (novelId, chapterNumber) => {
    try {
        const response = await Utils.apiRequest(`/novels/${novelId}/chapters`);
        if (response.success) {
            const chapters = response.data;
            const chapter = chapters.find(ch => ch.chapter_number == chapterNumber);
            if (chapter) {
                showChapterModal(chapter);
            }
        }
    } catch (error) {
        Utils.showMessage('加载章节失败: ' + error.message, 'danger');
    }
};

// 基于质量评估优化角色
window.optimizeCharactersBasedOnQuality = async () => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('正在基于质量评估优化角色...');
        
        // 首先检查是否有质量评估数据
        const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/character_quality_assessment`);
        
        if (!qualityResponse.success || !qualityResponse.data) {
            Utils.hideLoading();
            Utils.showMessage('请先进行角色质量评估', 'warning');
            return;
        }
        
        const qualityData = qualityResponse.data;
        const suggestions = qualityData.suggestions || [];
        
        if (suggestions.length === 0) {
            Utils.hideLoading();
            Utils.showMessage('质量评估显示角色已经很好，无需优化', 'info');
            return;
        }
        
        // 调用角色优化API
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/characters/improve`, {
            method: 'POST',
            body: JSON.stringify({
                suggestions: suggestions
            })
        });
        
        Utils.hideLoading();
        
        if (response.success) {
            Utils.showMessage('角色优化成功！', 'success');
            
            // 刷新角色详情显示
            const characterDetailsElement = document.getElementById('character-content');
            if (characterDetailsElement) {
                await StepDetailsManager.loadCharacterDetails(characterDetailsElement);
            }
            
            // 显示优化结果
            const result = response.data;
            if (result.quality_assessment) {
                const score = result.quality_assessment.overall_score;
                const level = result.quality_assessment.quality_level;
                Utils.showMessage(`优化完成！当前质量评分：${score}分 (${level})`, 'success');
            }
        } else {
            Utils.showMessage('角色优化失败: ' + (response.error || '未知错误'), 'danger');
        }
        
    } catch (error) {
        Utils.hideLoading();
        Utils.showMessage('角色优化失败: ' + error.message, 'danger');
    }
};

// 基于质量评估优化故事线
window.optimizeStorylineBasedOnQuality = async () => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('正在基于质量评估优化故事线...');
        
        // 首先检查是否有质量评估数据
        const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/storyline_quality_assessment`);
        
        if (!qualityResponse.success || !qualityResponse.data) {
            Utils.hideLoading();
            Utils.showMessage('请先进行故事线质量评估', 'warning');
            return;
        }
        
        const qualityData = qualityResponse.data;
        const suggestions = qualityData.suggestions || [];
        
        if (suggestions.length === 0) {
            Utils.hideLoading();
            Utils.showMessage('质量评估显示故事线已经很好，无需优化', 'info');
            return;
        }
        
        // 调用故事线优化API
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/storyline/improve`, {
            method: 'POST',
            body: JSON.stringify({
                suggestions: suggestions
            })
        });
        
        Utils.hideLoading();
        
        if (response.success) {
            const result = response.data;
            
            // 检查优化结果
            if (result.status === 'success') {
                Utils.showMessage('故事线优化成功！', 'success');
                
                // 显示优化结果
                if (result.quality_assessment) {
                    const score = result.quality_assessment.overall_score;
                    const level = result.quality_assessment.quality_level;
                    Utils.showMessage(`优化完成！当前质量评分：${score}分 (${level})`, 'success');
                }
            } else if (result.status === 'needs_improvement') {
                Utils.showMessage('故事线已优化，但仍有改进空间', 'warning');
                
                // 显示优化结果
                if (result.quality_assessment) {
                    const score = result.quality_assessment.overall_score;
                    const level = result.quality_assessment.quality_level;
                    Utils.showMessage(`优化完成！当前质量评分：${score}分 (${level})`, 'warning');
                }
            } else {
                Utils.showMessage('故事线优化完成，但状态未知', 'info');
            }
            
            // 刷新故事线详情显示
            const storylineDetailsElement = document.getElementById('storyline-content');
            if (storylineDetailsElement) {
                await StepDetailsManager.loadStorylineDetails(document.getElementById('step-details-storyline_generation'));
            }
        } else {
            Utils.showMessage('故事线优化失败: ' + (response.error || '未知错误'), 'danger');
        }
        
    } catch (error) {
        Utils.hideLoading();
        Utils.showMessage('故事线优化失败: ' + error.message, 'danger');
    }
};


// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', () => {
    // 设置表单提交事件
    document.getElementById('create-novel-form').addEventListener('submit', (e) => {
        e.preventDefault();
        window.createNovel();
    });
    
    // 设置字符计数
    const requirementsTextarea = document.getElementById('novel-requirements');
    const requirementsCount = document.getElementById('requirements-count');
    
    if (requirementsTextarea && requirementsCount) {
        requirementsTextarea.addEventListener('input', () => {
            const count = requirementsTextarea.value.length;
            requirementsCount.textContent = count;
            
            // 根据字符数改变颜色
            if (count > 1800) {
                requirementsCount.style.color = '#dc3545'; // 红色
            } else if (count > 1500) {
                requirementsCount.style.color = '#ffc107'; // 黄色
            } else {
                requirementsCount.style.color = '#6c757d'; // 灰色
            }
        });
    }
    
    // 初始化页面
    Navigation.showWelcome();
    
    // 显示欢迎消息
    Utils.showMessage('欢迎使用 InkAI 智能小说创作系统！', 'info', 3000);
});

// 续写编辑模式管理
const ContinuationEditModeManager = {
    currentEditMode: null,
    
    // 切换续写编辑模式
    toggleEditMode: (stepKey) => {
        if (ContinuationEditModeManager.currentEditMode === stepKey) {
            ContinuationEditModeManager.exitEditMode();
        } else {
            ContinuationEditModeManager.enterEditMode(stepKey);
        }
    },
    
    // 进入编辑模式
    enterEditMode: (stepKey) => {
        // 如果已经在编辑其他内容，先退出
        if (ContinuationEditModeManager.currentEditMode && ContinuationEditModeManager.currentEditMode !== stepKey) {
            ContinuationEditModeManager.exitEditMode();
        }
        
        ContinuationEditModeManager.currentEditMode = stepKey;
        
        // 为所有可编辑元素添加编辑功能
        const editableElements = document.querySelectorAll('.editable');
        editableElements.forEach(element => {
            element.contentEditable = true;
            element.classList.add('editing');
            element.addEventListener('blur', ContinuationEditModeManager.onContentChange);
            element.addEventListener('keydown', ContinuationEditModeManager.onKeyDown);
        });
        
        // 显示保存按钮
        const saveBtn = document.getElementById('save-continuation-storyline-btn');
        if (saveBtn) {
            saveBtn.style.display = 'inline-block';
        }
        
        Utils.showMessage('已进入编辑模式，点击内容进行修改', 'info');
    },
    
    // 退出编辑模式
    exitEditMode: () => {
        if (!ContinuationEditModeManager.currentEditMode) return;
        
        // 移除所有可编辑元素的编辑功能
        const editableElements = document.querySelectorAll('.editable');
        editableElements.forEach(element => {
            element.contentEditable = false;
            element.classList.remove('editing');
            element.removeEventListener('blur', ContinuationEditModeManager.onContentChange);
            element.removeEventListener('keydown', ContinuationEditModeManager.onKeyDown);
        });
        
        // 隐藏保存按钮
        const saveBtn = document.getElementById('save-continuation-storyline-btn');
        if (saveBtn) {
            saveBtn.style.display = 'none';
        }
        
        ContinuationEditModeManager.currentEditMode = null;
        Utils.showMessage('已退出编辑模式', 'info');
    },
    
    // 内容变化处理
    onContentChange: (event) => {
        // 可以在这里添加实时保存或其他处理逻辑
    },
    
    // 键盘事件处理
    onKeyDown: (event) => {
        if (event.key === 'Escape') {
            ContinuationEditModeManager.exitEditMode();
        }
    },
    
    // 获取修改后的内容
    getModifiedContent: () => {
        const modifiedContent = {};
        const editableElements = document.querySelectorAll('.editable');
        
        editableElements.forEach(element => {
            const field = element.getAttribute('data-field');
            if (field) {
                // 处理嵌套字段（如 scene_setting.time）
                const fieldParts = field.split('.');
                if (fieldParts.length === 1) {
                    modifiedContent[field] = element.textContent.trim();
                } else if (fieldParts.length === 2) {
                    if (!modifiedContent[fieldParts[0]]) {
                        modifiedContent[fieldParts[0]] = {};
                    }
                    modifiedContent[fieldParts[0]][fieldParts[1]] = element.textContent.trim();
                }
            }
        });
        
        return modifiedContent;
    }
};

// 续写内容保存管理
const ContinuationContentSaveManager = {
    // 保存续写故事线内容
    saveStorylineContent: async () => {
        if (!AppState.currentNovelId) {
            Utils.showMessage('没有活跃的小说项目', 'warning');
            return;
        }
        
        try {
            Utils.showLoading('正在保存修改...');
            
            const modifiedContent = ContinuationEditModeManager.getModifiedContent();
            
            // 调用API保存修改
            const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/storyline`, {
                method: 'PUT',
                body: JSON.stringify(modifiedContent)
            });
            
            if (response.success) {
                Utils.showMessage('续写故事线修改保存成功！', 'success');
                ContinuationEditModeManager.exitEditMode();
                // 只重新加载当前的故事线详情，不重新加载整个工作流程
                const currentStepElement = document.querySelector('.step-item.current .step-details');
                if (currentStepElement) {
                    await ContinuationManager.loadContinuationStorylineDetails(currentStepElement);
                }
            } else {
                Utils.showMessage('保存失败: ' + (response.message || '未知错误'), 'danger');
            }
        } catch (error) {
            Utils.showMessage('保存失败: ' + error.message, 'danger');
        } finally {
            Utils.hideLoading();
        }
    }
};

// 续写质量评估和优化函数
window.assessContinuationQuality = async (contentType) => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('正在进行质量评估...');
        
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/quality`, {
            method: 'POST',
            body: JSON.stringify({ content_type: contentType })
        });
        
        if (response.success) {
            Utils.showMessage('质量评估完成！', 'success');
            // 根据内容类型重新加载相应的详情
            const currentStepElement = document.querySelector('.step-item.current .step-details');
            if (currentStepElement) {
                if (contentType === 'storyline') {
                    await ContinuationManager.loadContinuationStorylineDetails(currentStepElement);
                } else if (contentType === 'story') {
                    await StepDetailsManager.loadContinuationChapterDetails(currentStepElement);
                }
            }
        } else {
            Utils.showMessage('质量评估失败: ' + (response.message || '未知错误'), 'danger');
        }
    } catch (error) {
        Utils.showMessage('质量评估失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

window.optimizeContinuationStorylineBasedOnQuality = async () => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('正在基于质量评估优化故事线...');
        
        // 首先检查是否有质量评估数据
        const qualityResponse = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/data/continuation_storyline_quality_assessment`);
        
        if (!qualityResponse.success || !qualityResponse.data) {
            Utils.hideLoading();
            Utils.showMessage('请先进行续写故事线质量评估', 'warning');
            return;
        }
        
        const qualityData = qualityResponse.data;
        const suggestions = qualityData.suggestions || [];
        
        if (suggestions.length === 0) {
            Utils.hideLoading();
            Utils.showMessage('质量评估显示续写故事线已经很好，无需优化', 'info');
            return;
        }
        
        // 调用续写故事线优化API
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/storyline/improve`, {
            method: 'POST',
            body: JSON.stringify({
                suggestions: suggestions
            })
        });
        
        Utils.hideLoading();
        
        if (response.success) {
            const result = response.data;
            if (result.status === 'success') {
                Utils.showMessage('续写故事线优化完成！', 'success');
                
                // 显示优化结果
                if (result.quality_assessment) {
                    const score = result.quality_assessment.overall_score;
                    const level = result.quality_assessment.quality_level;
                    Utils.showMessage(`优化完成！当前质量评分：${score}分 (${level})`, 'success');
                }
            } else if (result.status === 'needs_improvement') {
                Utils.showMessage('续写故事线已优化，但仍有改进空间', 'warning');
                
                // 显示优化结果
                if (result.quality_assessment) {
                    const score = result.quality_assessment.overall_score;
                    const level = result.quality_assessment.quality_level;
                    Utils.showMessage(`优化完成！当前质量评分：${score}分 (${level})`, 'warning');
                }
            } else {
                Utils.showMessage('续写故事线优化完成，但状态未知', 'info');
            }
            
            // 只重新加载当前的故事线详情以显示优化结果
            const currentStepElement = document.querySelector('.step-item.current .step-details');
            if (currentStepElement) {
                await ContinuationManager.loadContinuationStorylineDetails(currentStepElement);
            }
        } else {
            Utils.showMessage('续写故事线优化失败: ' + (response.error || '未知错误'), 'danger');
        }
    } catch (error) {
        Utils.showMessage('续写故事线优化失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 续写步骤操作函数
window.regenerateContinuationStep = async (stepKey) => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading(`正在重新生成续写${stepKey}...`);
        
        // 根据步骤类型调用相应的API
        switch (stepKey) {
            case 'storyline_generation':
                await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/storyline`, {
                    method: 'POST'
                });
                break;
            case 'chapter_writing':
                await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/chapter`, {
                    method: 'POST'
                });
                break;
            default:
                throw new Error('未知的续写步骤: ' + stepKey);
        }
        
        Utils.showMessage(`续写${stepKey}重新生成成功！`, 'success');
        
        // 重新加载续写工作流程状态
        await ContinuationManager.loadContinuationWorkflow(AppState.currentNovelId);
        
    } catch (error) {
        Utils.showMessage(`重新生成续写${stepKey}失败: ` + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

window.improveContinuationStep = async (stepKey) => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    // 显示改进对话框
    const improvementType = stepKey === 'storyline_generation' ? 'storyline' : 'chapter';
    showContinuationImprovementDialog(improvementType);
};

// 显示续写改进对话框
const showContinuationImprovementDialog = (type) => {
    const modalHtml = `
        <div class="modal fade" id="continuationImprovementModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-magic me-2"></i>
                            改进续写${type === 'storyline' ? '故事线' : '章节'}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label for="continuation-improvement-suggestions" class="form-label">
                                改进建议（可选，留空将使用AI自动分析）
                            </label>
                            <textarea class="form-control" id="continuation-improvement-suggestions" rows="4" 
                                      placeholder="请输入具体的改进建议，例如：增加更多细节描写，加强人物对话等"></textarea>
                        </div>
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            如果不填写改进建议，系统将自动分析当前内容并提供改进方案。
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="confirmContinuationImprovement('${type}')">
                            <i class="fas fa-magic me-2"></i>开始改进
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除已存在的模态框
    const existingModal = document.getElementById('continuationImprovementModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新的模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('continuationImprovementModal'));
    modal.show();
};

// 确认续写改进
window.confirmContinuationImprovement = async (type) => {
    const suggestions = document.getElementById('continuation-improvement-suggestions').value.trim();
    
    try {
        Utils.showLoading(`正在改进续写${type}...`);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('continuationImprovementModal'));
        modal.hide();
        
        // 调用改进API
        let response;
        if (type === 'storyline') {
            response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/storyline/improve`, {
                method: 'POST',
                body: JSON.stringify({
                    suggestions: suggestions ? [suggestions] : []
                })
            });
        } else if (type === 'chapter') {
            response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/chapter/improve`, {
                method: 'POST',
                body: JSON.stringify({
                    suggestions: suggestions ? [suggestions] : []
                })
            });
        }
        
        Utils.hideLoading();
        
        if (response.success) {
            Utils.showMessage(`续写${type}改进成功！`, 'success');
            // 重新加载续写工作流程状态
            await ContinuationManager.loadContinuationWorkflow(AppState.currentNovelId);
        } else {
            Utils.showMessage(`续写${type}改进失败: ` + (response.error || '未知错误'), 'danger');
        }
    } catch (error) {
        Utils.hideLoading();
        Utils.showMessage(`续写${type}改进失败: ` + error.message, 'danger');
    }
};

// 清除续写章节错误缓存
window.clearContinuationChapterCache = async () => {
    if (!AppState.currentNovelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('正在清除错误数据...');
        
        // 调用后端API清除错误的缓存数据
        const response = await Utils.apiRequest(`/novels/${AppState.currentNovelId}/continuation/clear-cache`, {
            method: 'POST'
        });
        
        if (response.success) {
            Utils.showMessage('错误数据已清除，请重新生成续写章节', 'success');
            // 重新加载续写工作流程状态
            await ContinuationManager.loadContinuationWorkflow(AppState.currentNovelId);
        } else {
            Utils.showMessage('清除错误数据失败: ' + (response.error || '未知错误'), 'danger');
        }
    } catch (error) {
        Utils.showMessage('清除错误数据失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 快速续写功能
window.showQuickContinuationDialog = () => {
    // 检查是否有选中的小说
    const novelId = AppState.selectedNovelId || AppState.currentNovelId;
    if (!novelId) {
        Utils.showMessage('请先选择要续写的小说', 'warning');
        return;
    }
    
    console.log('显示快速续写对话框 - 小说ID:', novelId);
    const modalHtml = `
        <div class="modal fade" id="quickContinuationModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-success text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-bolt me-2"></i>
                            快速续写设置
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card h-100 border-primary">
                                    <div class="card-header bg-primary text-white">
                                        <h6 class="mb-0">
                                            <i class="fas fa-target me-2"></i>
                                            指定章节数
                                        </h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label class="form-label">续写章节数量</label>
                                            <input type="number" class="form-control" id="chapterCount" 
                                                   min="1" max="10" value="1" placeholder="输入要续写的章节数">
                                            <div class="form-text">建议1-5章，最多10章</div>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">续写需求（可选）</label>
                                            <textarea class="form-control" id="quickRequirements" rows="3" 
                                                      placeholder="描述您希望续写的内容方向或特殊要求..."></textarea>
                                        </div>
                                        <button class="btn btn-primary w-100" onclick="startQuickContinuation('fixed')">
                                            <i class="fas fa-play me-2"></i>
                                            开始续写指定章节数
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card h-100 border-success">
                                    <div class="card-header bg-success text-white">
                                        <h6 class="mb-0">
                                            <i class="fas fa-infinity me-2"></i>
                                            持续写作
                                        </h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="mb-3">
                                            <label class="form-label">写作模式</label>
                                            <select class="form-select" id="continuousMode">
                                                <option value="auto">自动模式 - AI自主决定何时停止（最多50章）</option>
                                                <option value="infinite">无限模式 - 持续写作直到故事自然结束</option>
                                                <option value="manual">手动模式 - 每章完成后询问是否继续</option>
                                            </select>
                                        </div>
                                        <div class="mb-3">
                                            <label class="form-label">续写需求（可选）</label>
                                            <textarea class="form-control" id="continuousRequirements" rows="3" 
                                                      placeholder="描述您希望续写的内容方向或特殊要求..."></textarea>
                                        </div>
                                        <button class="btn btn-success w-100" onclick="startQuickContinuation('continuous')">
                                            <i class="fas fa-infinity me-2"></i>
                                            开始持续写作
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <div class="alert alert-info border-0">
                                <div class="d-flex align-items-start">
                                    <i class="fas fa-info-circle fa-2x text-info me-3 mt-1"></i>
                                    <div>
                                        <h6 class="alert-heading mb-2">快速续写说明</h6>
                                        <ul class="mb-0 small">
                                            <li><strong>指定章节数</strong>：系统将自动执行完整的续写流程（故事线生成 → 章节写作）直到完成指定数量的章节</li>
                                            <li><strong>持续写作</strong>：系统将持续生成章节，支持三种模式：
                                                <ul>
                                                    <li><strong>自动模式</strong>：AI自主决定何时停止（最多50章）</li>
                                                    <li><strong>无限模式</strong>：持续写作直到故事自然结束，无章节数限制</li>
                                                    <li><strong>手动模式</strong>：每章完成后询问是否继续</li>
                                                </ul>
                                            </li>
                                            <li><strong>智能结束检测</strong>：无限模式会自动检测故事结束点（如"完结"、"大结局"等关键词）</li>
                                            <li><strong>自动保存</strong>：每章完成后会自动保存，您可以随时查看进度</li>
                                            <li><strong>流程一致</strong>：快速续写使用与手动续写相同的AI工作流程，确保质量</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除已存在的模态框
    const existingModal = document.getElementById('quickContinuationModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新的模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('quickContinuationModal'));
    modal.show();
};

// 开始快速续写
window.startQuickContinuation = async (mode) => {
    // 优先使用 selectedNovelId（续写选择页面），如果没有则使用 currentNovelId（工作流程页面）
    const novelId = AppState.selectedNovelId || AppState.currentNovelId;
    
    if (!novelId) {
        Utils.showMessage('没有活跃的小说项目', 'warning');
        return;
    }
    
    console.log('快速续写 - 使用小说ID:', novelId);
    
    try {
        let config = {};
        
        if (mode === 'fixed') {
            const chapterCount = parseInt(document.getElementById('chapterCount').value);
            const requirements = document.getElementById('quickRequirements').value.trim();
            
            if (!chapterCount || chapterCount < 1 || chapterCount > 10) {
                Utils.showMessage('请输入有效的章节数量（1-10）', 'warning');
                return;
            }
            
            config = {
                mode: 'fixed',
                chapter_count: chapterCount,
                requirements: requirements
            };
        } else if (mode === 'continuous') {
            const continuousMode = document.getElementById('continuousMode').value;
            const requirements = document.getElementById('continuousRequirements').value.trim();
            
            config = {
                mode: 'continuous',
                continuous_mode: continuousMode,
                requirements: requirements
            };
        }
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('quickContinuationModal'));
        if (modal) {
            modal.hide();
        }
        
        Utils.showLoading('正在启动快速续写...');
        
        // 调用后端API启动快速续写
        const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick`, {
            method: 'POST',
            body: JSON.stringify(config)
        });
        
        if (response.success) {
            Utils.showMessage('快速续写已启动！', 'success');
            // 设置当前小说ID并跳转到快速续写进度页面
            AppState.currentNovelId = novelId;
            AppState.quickContinuationTaskId = response.data.task_id;
            Navigation.showQuickContinuationProgress(novelId);
        } else {
            Utils.showMessage('启动快速续写失败: ' + (response.error || '未知错误'), 'danger');
        }
        
    } catch (error) {
        Utils.showMessage('启动快速续写失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 检查快速续写进度
window.checkQuickContinuationProgress = async () => {
    const novelId = AppState.selectedNovelId || AppState.currentNovelId;
    if (!novelId) {
        Utils.showMessage('请先选择小说', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('检查快速续写进度...');
        const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick/progress`);
        
        if (response.success) {
            // 有进度数据，跳转到进度页面
            AppState.quickContinuationProgress = response.data;
            Navigation.showQuickContinuationProgress(novelId);
            Utils.showMessage('找到快速续写任务，正在显示进度', 'success');
        } else {
            // 没有进度数据，询问是否启动新的快速续写
            if (response.error === '未找到快速续写任务') {
                const startNew = confirm('当前没有运行中的快速续写任务，是否启动新的快速续写？');
                if (startNew) {
                    showQuickContinuationDialog();
                }
            } else {
                Utils.showMessage('检查进度失败: ' + response.error, 'danger');
            }
        }
    } catch (error) {
        Utils.showMessage('检查进度失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 为指定小说检查快速续写进度
window.checkQuickContinuationProgressForNovel = async (novelId) => {
    try {
        Utils.showLoading('检查快速续写进度...');
        const response = await Utils.apiRequest(`/novels/${novelId}/continuation/quick/progress`);
        
        if (response.success) {
            // 有进度数据，跳转到进度页面
            AppState.quickContinuationProgress = response.data;
            AppState.currentNovelId = novelId;
            Navigation.showQuickContinuationProgress(novelId);
            Utils.showMessage('找到快速续写任务，正在显示进度', 'success');
        } else {
            // 没有进度数据，询问是否启动新的快速续写
            if (response.error === '未找到快速续写任务') {
                const startNew = confirm('当前没有运行中的快速续写任务，是否启动新的快速续写？');
                if (startNew) {
                    AppState.selectedNovelId = novelId;
                    showQuickContinuationDialog();
                }
            } else {
                Utils.showMessage('检查进度失败: ' + response.error, 'danger');
            }
        }
    } catch (error) {
        Utils.showMessage('检查进度失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 映射快速续写步骤到标准节点
const mapQuickStepToNode = (quickStep) => {
    // 增强版流程映射
    if (quickStep.includes('context_preparation')) return 'context_preparation';
    if (quickStep.includes('storyline_generation')) return 'storyline_generation';
    if (quickStep.includes('knowledge_update')) return 'knowledge_update';
    if (quickStep.includes('content_generation')) return 'content_generation';
    if (quickStep.includes('quality_assessment')) return 'quality_assessment';
    if (quickStep.includes('content_improvement')) return 'content_improvement';
    if (quickStep.includes('final_validation')) return 'final_validation';
    
    // 兼容旧版本步骤
    if (quickStep.includes('generating_storyline')) return 'storyline_generation';
    if (quickStep.includes('assessing_storyline_quality')) return 'quality_assessment';
    if (quickStep.includes('improving_storyline')) return 'content_improvement';
    if (quickStep.includes('writing_chapter')) return 'content_generation';
    if (quickStep.includes('assessing_chapter_quality')) return 'quality_assessment';
    if (quickStep.includes('improving_chapter')) return 'content_improvement';
    if (quickStep.includes('saving_chapter')) return 'final_validation';
    if (quickStep.includes('chapter_completed')) return 'final_validation';
    
    if (quickStep === 'completed') return 'final_validation';
    if (quickStep === 'starting' || quickStep === 'initializing') return 'context_preparation';
    return 'context_preparation'; // 默认
};

// 显示快速续写进度（8节点流程图）
const displayQuickContinuationProgress = (progress) => {
    const container = document.getElementById('quick-continuation-progress-container');
    if (!container) return;
    
    const statusColors = {
        'running': 'primary',
        'completed': 'success',
        'failed': 'danger',
        'paused': 'warning',
        'stopped': 'secondary'
    };
    
    const statusTexts = {
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
        'paused': '已暂停',
        'stopped': '已停止'
    };
    
    // 为所有字段提供默认值，确保容错处理
    const safeProgress = {
        novel_id: progress.novel_id || 'unknown',
        novel_title: progress.novel_title || '未知小说',
        mode: progress.mode || 'fixed',
        continuous_mode: progress.continuous_mode || 'auto',
        total_chapters: progress.total_chapters || 0,
        completed_chapters: progress.completed_chapters || 0,
        current_chapter: progress.current_chapter || 1,
        current_step: progress.current_step || 'unknown',
        status: progress.status || 'unknown',
        start_time: progress.start_time || '',
        last_update: progress.last_update || '',
        error_message: progress.error_message || '',
        chapter_details: progress.chapter_details || []
    };
    
    const progressPercentage = safeProgress.total_chapters > 0 ? 
        Math.round((safeProgress.completed_chapters / safeProgress.total_chapters) * 100) : 0;
    
    // 映射当前步骤到节点
    const currentNode = mapQuickStepToNode(safeProgress.current_step);
    
    // 定义增强版7个节点
    const nodes = [
        { key: 'context_preparation', name: '上下文准备', icon: 'fas fa-database' },
        { key: 'storyline_generation', name: '双层故事线生成', icon: 'fas fa-route' },
        { key: 'knowledge_update', name: '知识图谱更新', icon: 'fas fa-project-diagram' },
        { key: 'content_generation', name: '内容生成', icon: 'fas fa-pen-fancy' },
        { key: 'quality_assessment', name: '质量评估', icon: 'fas fa-clipboard-check' },
        { key: 'content_improvement', name: '内容改进', icon: 'fas fa-magic', conditional: true },
        { key: 'final_validation', name: '最终验证', icon: 'fas fa-check-circle' }
    ];
    
    // 生成节点HTML
    const nodesHtml = nodes.map((node, index) => {
        let nodeStatus = 'pending';
        
        // 确定节点状态
        const currentNodeIndex = nodes.findIndex(n => n.key === currentNode);
        
        if (index < currentNodeIndex) {
            nodeStatus = 'completed';
        } else if (index === currentNodeIndex) {
            nodeStatus = 'current';
        } else {
            nodeStatus = 'pending';
        }
        
        // 对于条件性节点，检查是否被跳过
        if (node.conditional && index < currentNodeIndex) {
            // 检查是否实际执行了这个步骤
            const wasExecuted = safeProgress.current_step.includes(node.key.split('_')[0]);
            if (!wasExecuted) {
                nodeStatus = 'skipped';
            }
        }
        
        return `
            <div class="process-node ${nodeStatus}">
                <div class="node-icon">
                    <i class="${node.icon}"></i>
                </div>
                <div class="node-content">
                    <div class="node-title">${node.name}</div>
                    ${node.conditional ? '<div class="node-badge">按需</div>' : ''}
                </div>
                <div class="node-status">
                    ${nodeStatus === 'completed' ? '<i class="fas fa-check-circle text-success"></i>' :
                      nodeStatus === 'current' ? '<i class="fas fa-play-circle text-primary"></i>' :
                      nodeStatus === 'skipped' ? '<i class="fas fa-forward text-warning"></i>' :
                      '<i class="fas fa-circle text-muted"></i>'}
                </div>
                ${index < nodes.length - 1 ? '<div class="node-connector"></div>' : ''}
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="quick-continuation-progress">
            <!-- 任务信息卡片 -->
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-${statusColors[safeProgress.status] || 'secondary'} text-white">
                    <div class="d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">
                            <i class="fas fa-bolt me-2"></i>快速续写进度
                        </h4>
                        <div class="workflow-nav-buttons">
                            <button type="button" class="btn btn-light btn-sm me-2" onclick="goToContinuationNovelList()">
                                <i class="fas fa-arrow-left me-1"></i>返回续写列表
                            </button>
                            <button type="button" class="btn btn-outline-light btn-sm" onclick="goToHome()">
                                <i class="fas fa-home me-1"></i>首页
                            </button>
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h5 class="card-title">${safeProgress.novel_title}</h5>
                            <div class="row mb-3">
                                <div class="col-sm-6">
                                    <div class="info-item">
                                        <i class="fas fa-cog text-primary me-2"></i>
                                        <strong>模式:</strong> ${safeProgress.mode === 'fixed' ? '指定章节数' : 
                                            (safeProgress.continuous_mode === 'infinite' ? '无限续写' : 
                                            (safeProgress.continuous_mode === 'auto' ? '自动模式' : '手动模式'))}
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="info-item">
                                        <i class="fas fa-clock text-info me-2"></i>
                                        <strong>状态:</strong> 
                                        <span class="badge bg-${statusColors[safeProgress.status] || 'secondary'}">${statusTexts[safeProgress.status] || '未知'}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="row mb-3">
                                <div class="col-sm-6">
                                    <div class="info-item">
                                        <i class="fas fa-chapter text-success me-2"></i>
                                        <strong>进度:</strong> ${safeProgress.completed_chapters}/${safeProgress.total_chapters} 章
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="info-item">
                                        <i class="fas fa-play text-warning me-2"></i>
                                        <strong>当前:</strong> 第${safeProgress.current_chapter}章
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 增强功能信息 -->
                            ${progress.quality_scores && progress.quality_scores.length > 0 ? `
                                <div class="row mb-3">
                                    <div class="col-sm-6">
                                        <div class="info-item">
                                            <i class="fas fa-star text-warning me-2"></i>
                                            <strong>平均质量:</strong> ${(progress.quality_scores.reduce((a, b) => a + b, 0) / progress.quality_scores.length).toFixed(1)}分
                                        </div>
                                    </div>
                                    <div class="col-sm-6">
                                        <div class="info-item">
                                            <i class="fas fa-memory text-info me-2"></i>
                                            <strong>内存使用:</strong> ${progress.memory_usage ? progress.memory_usage.toFixed(1) : 0}%
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${progress.performance_metrics && Object.keys(progress.performance_metrics).length > 0 ? `
                                <div class="row mb-3">
                                    <div class="col-sm-12">
                                        <div class="info-item">
                                            <i class="fas fa-tachometer-alt text-primary me-2"></i>
                                            <strong>性能指标:</strong>
                                            <span class="badge bg-success ms-2">双层故事线</span>
                                            <span class="badge bg-info ms-1">动态知识图谱</span>
                                            <span class="badge bg-warning ms-1">智能内存管理</span>
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            <!-- 8节点流程图 -->
                            <div class="process-flow mb-3">
                                <h6 class="mb-3"><i class="fas fa-sitemap me-2"></i>当前章节执行流程</h6>
                                <div class="process-nodes">
                                    ${nodesHtml}
                                </div>
                            </div>
                            
                            ${safeProgress.error_message ? `
                                <div class="alert alert-danger">
                                    <i class="fas fa-exclamation-triangle me-2"></i>
                                    ${safeProgress.error_message}
                                </div>
                            ` : ''}
                        </div>
                        <div class="col-md-4">
                            <div class="task-controls">
                                <h6 class="mb-3">任务控制</h6>
                                ${safeProgress.status === 'running' ? `
                                    <button class="btn btn-warning btn-sm w-100 mb-2" onclick="QuickContinuationManager.pauseTask('${safeProgress.novel_id}')">
                                        <i class="fas fa-pause me-2"></i>暂停任务
                                    </button>
                                    <button class="btn btn-danger btn-sm w-100" onclick="QuickContinuationManager.stopTask('${safeProgress.novel_id}')">
                                        <i class="fas fa-stop me-2"></i>停止任务
                                    </button>
                                ` : safeProgress.status === 'paused' ? `
                                    <button class="btn btn-success btn-sm w-100 mb-2" onclick="QuickContinuationManager.resumeTask('${safeProgress.novel_id}')">
                                        <i class="fas fa-play me-2"></i>恢复任务
                                    </button>
                                    <button class="btn btn-danger btn-sm w-100" onclick="QuickContinuationManager.stopTask('${safeProgress.novel_id}')">
                                        <i class="fas fa-stop me-2"></i>停止任务
                                    </button>
                                ` : safeProgress.status === 'completed' ? `
                                    <button class="btn btn-primary btn-sm w-100 mb-2" onclick="Navigation.showContinuationWorkflow('${safeProgress.novel_id}')">
                                        <i class="fas fa-eye me-2"></i>查看续写结果
                                    </button>
                                    <button class="btn btn-success btn-sm w-100" onclick="showQuickContinuationDialog()">
                                        <i class="fas fa-plus me-2"></i>继续续写
                                    </button>
                                ` : `
                                    <button class="btn btn-primary btn-sm w-100" onclick="showQuickContinuationDialog()">
                                        <i class="fas fa-redo me-2"></i>重新开始
                                    </button>
                                `}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 章节详情 -->
            ${safeProgress.chapter_details && safeProgress.chapter_details.length > 0 ? `
                <div class="card border-0 shadow-sm">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-list me-2"></i>章节详情
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            ${safeProgress.chapter_details.map(chapter => `
                                <div class="col-md-4 mb-3">
                                    <div class="chapter-detail-card">
                                        <div class="d-flex align-items-center">
                                            <div class="chapter-number me-3">
                                                <span class="badge bg-primary">第${chapter.chapter_number || '?'}章</span>
                                            </div>
                                            <div class="chapter-status">
                                                <i class="fas fa-check-circle text-success"></i>
                                                <small class="text-muted ms-1">${Utils.formatDate(chapter.completed_at || '')}</small>
                                            </div>
                                        </div>
                                        ${chapter.quality_score ? `
                                            <div class="mt-2">
                                                <small class="text-warning">
                                                    <i class="fas fa-star me-1"></i>
                                                    质量: ${chapter.quality_score}分
                                                </small>
                                            </div>
                                        ` : ''}
                                        ${chapter.word_count ? `
                                            <div class="mt-1">
                                                <small class="text-info">
                                                    <i class="fas fa-file-text me-1"></i>
                                                    ${chapter.word_count}字
                                                </small>
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
};

// 更新快速续写进度
const updateQuickContinuationProgress = (progress) => {
    // 更新进度条
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        const progressPercentage = progress.total_chapters > 0 ? 
            Math.round((progress.completed_chapters / progress.total_chapters) * 100) : 0;
        progressBar.style.width = `${progressPercentage}%`;
        progressBar.textContent = `${progressPercentage}%`;
        progressBar.className = `progress-bar bg-${getStatusColor(progress.status)}`;
    }
    
    // 更新状态
    const statusBadge = document.querySelector('.badge');
    if (statusBadge) {
        statusBadge.className = `badge bg-${getStatusColor(progress.status)}`;
        statusBadge.textContent = getStatusText(progress.status);
    }
    
    // 更新当前步骤
    const currentStepElement = document.querySelector('.info-item:last-child');
    if (currentStepElement) {
        console.log('更新当前步骤:', progress.current_step, '章节:', progress.current_chapter);
        currentStepElement.innerHTML = `
            <i class="fas fa-play text-warning me-2"></i>
            <strong>当前:</strong> 第${progress.current_chapter}章 - ${getQuickContinuationStepDisplayName(progress.current_step)}
        `;
    }
    
    // 修复：更新章节详情列表
    updateChapterDetailsList(progress);
    
    // 更新错误信息
    if (progress.error_message) {
        let errorAlert = document.querySelector('.alert-danger');
        if (!errorAlert) {
            const progressContainer = document.querySelector('.quick-continuation-progress .card-body .row .col-md-8');
            if (progressContainer) {
                progressContainer.insertAdjacentHTML('beforeend', `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        ${progress.error_message}
                    </div>
                `);
            }
        }
    }
};

// 更新章节详情列表
const updateChapterDetailsList = (progress) => {
    // 查找章节详情容器
    const chapterDetailsContainer = document.querySelector('.quick-continuation-progress .card:last-child .card-body .row');
    
    if (chapterDetailsContainer && progress.chapter_details && progress.chapter_details.length > 0) {
        console.log('更新章节详情列表，章节数:', progress.chapter_details.length);
        
        // 重新渲染章节详情列表
        chapterDetailsContainer.innerHTML = progress.chapter_details.map(chapter => `
            <div class="col-md-4 mb-3">
                <div class="chapter-detail-card">
                    <div class="d-flex align-items-center">
                        <div class="chapter-number me-3">
                            <span class="badge bg-primary">第${chapter.chapter_number}章</span>
                        </div>
                        <div class="chapter-status">
                            <i class="fas fa-check-circle text-success"></i>
                            <small class="text-muted ms-1">${Utils.formatDate(chapter.completed_at)}</small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        console.log('章节详情列表已更新');
    } else if (progress.chapter_details && progress.chapter_details.length > 0) {
        // 如果章节详情容器不存在，但有待显示的章节，则重新渲染整个章节详情卡片
        console.log('章节详情容器不存在，重新渲染章节详情卡片');
        renderChapterDetailsCard(progress);
    }
};

// 渲染章节详情卡片
const renderChapterDetailsCard = (progress) => {
    const quickContinuationProgress = document.querySelector('.quick-continuation-progress');
    if (!quickContinuationProgress) return;
    
    // 查找现有的章节详情卡片
    let chapterDetailsCard = quickContinuationProgress.querySelector('.card:last-child');
    
    // 如果章节详情卡片不存在，创建新的
    if (!chapterDetailsCard || !chapterDetailsCard.querySelector('.card-header h5').textContent.includes('章节详情')) {
        chapterDetailsCard = document.createElement('div');
        chapterDetailsCard.className = 'card border-0 shadow-sm';
        quickContinuationProgress.appendChild(chapterDetailsCard);
    }
    
    // 更新章节详情卡片内容
    chapterDetailsCard.innerHTML = `
        <div class="card-header">
            <h5 class="mb-0">
                <i class="fas fa-list me-2"></i>章节详情
            </h5>
        </div>
        <div class="card-body">
            <div class="row">
                ${progress.chapter_details.map(chapter => `
                    <div class="col-md-4 mb-3">
                        <div class="chapter-detail-card">
                            <div class="d-flex align-items-center">
                                <div class="chapter-number me-3">
                                    <span class="badge bg-primary">第${chapter.chapter_number}章</span>
                                </div>
                                <div class="chapter-status">
                                    <i class="fas fa-check-circle text-success"></i>
                                    <small class="text-muted ms-1">${Utils.formatDate(chapter.completed_at)}</small>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    console.log('章节详情卡片已重新渲染');
};

// 获取状态颜色
const getStatusColor = (status) => {
    const colors = {
        'running': 'primary',
        'completed': 'success',
        'failed': 'danger',
        'paused': 'warning',
        'stopped': 'secondary'
    };
    return colors[status] || 'secondary';
};

// 获取状态文本
const getStatusText = (status) => {
    const texts = {
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
        'paused': '已暂停',
        'stopped': '已停止'
    };
    return texts[status] || '未知';
};

// 获取快速续写步骤显示名称
const getQuickContinuationStepDisplayName = (step) => {
    const stepNames = {
        'initializing': '初始化中',
        'starting': '启动中',
        'generating_storyline_chapter_': '生成故事线',
        'improving_storyline_chapter_': '改进故事线',
        'assessing_storyline_quality_chapter_': '评估故事线质量',
        'writing_chapter_': '写作章节',
        'assessing_chapter_quality_chapter_': '评估章节质量',
        'saving_chapter_': '保存章节',
        'chapter_completed_': '章节完成',
        'completed': '已完成',
        'failed': '失败',
        'paused': '已暂停',
        'stopped': '已停止'
    };
    
    // 添加调试信息
    console.log('步骤名称映射:', step, '->', stepNames);
    
    for (const [key, value] of Object.entries(stepNames)) {
        if (step.startsWith(key)) {
            console.log('匹配到步骤:', key, '->', value);
            return value;
        }
    }
    
    console.log('未匹配到步骤，返回原始值:', step);
    return step;
};

// 查看章节工作流
window.viewChapterWorkflow = async (novelId, chapterNumber) => {
    try {
        Utils.showLoading('加载章节工作流...');
        
        // 获取各个模块的具体内容
        const workflowData = await loadWorkflowModules(novelId, chapterNumber);
        
        // 显示章节工作流模态框
        showChapterWorkflowModal(novelId, chapterNumber, workflowData);
        
    } catch (error) {
        Utils.showMessage('加载章节工作流失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 显示章节工作流模态框
const showChapterWorkflowModal = (novelId, chapterNumber, workflowData) => {
    const modalHtml = `
        <div class="modal fade" id="chapterWorkflowModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-cogs me-2"></i>
                            第${chapterNumber}章工作流程
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="workflow-modules">
                            <!-- 故事线模块 - 全宽显示 -->
                            <div class="row mb-4">
                                <div class="col-12">
                                    <div class="workflow-module card">
                                        <div class="card-header bg-primary text-white">
                                            <h6 class="mb-0"><i class="fas fa-route me-2"></i>故事线</h6>
                                        </div>
                                        <div class="card-body">
                                            ${workflowData.storyline ? `
                                                <div class="storyline-content">
                                                    <div class="row">
                                                        <div class="col-md-8">
                                                            <h5 class="text-primary mb-3">${workflowData.storyline.chapter_title || '未知章节'}</h5>
                                                            <div class="storyline-details">
                                                                <div class="mb-3">
                                                                    <h6 class="text-secondary">章节概要</h6>
                                                                    <div class="chapter-summary p-3 bg-light rounded">
                                                                        ${workflowData.storyline.chapter_summary || '暂无概要'}
                                                                    </div>
                                                                </div>
                                                                <div class="mb-3">
                                                                    <h6 class="text-secondary">关键事件</h6>
                                                                    <div class="key-events p-3 bg-light rounded">
                                                                        ${Array.isArray(workflowData.storyline.key_events) ? 
                                                                            workflowData.storyline.key_events.map(event => `<div class="event-item mb-2">• ${event}</div>`).join('') : 
                                                                            (workflowData.storyline.key_events || '暂无关键事件')}
                                                                    </div>
                                                                </div>
                                                                ${workflowData.storyline.character_development ? `
                                                                    <div class="mb-3">
                                                                        <h6 class="text-secondary">人物发展</h6>
                                                                        <div class="character-development p-3 bg-light rounded">
                                                                            ${workflowData.storyline.character_development}
                                                                        </div>
                                                                    </div>
                                                                ` : ''}
                                                                ${workflowData.storyline.foreshadowing && workflowData.storyline.foreshadowing.length > 0 ? `
                                                                    <div class="mb-3">
                                                                        <h6 class="text-secondary">伏笔设置</h6>
                                                                        <div class="foreshadowing p-3 bg-light rounded">
                                                                            ${workflowData.storyline.foreshadowing.map(foreshadow => `<div class="foreshadow-item mb-2">• ${foreshadow}</div>`).join('')}
                                                                        </div>
                                                                    </div>
                                                                ` : ''}
                                                                ${workflowData.storyline.next_chapter_hint ? `
                                                                    <div class="mb-3">
                                                                        <h6 class="text-secondary">下章预告</h6>
                                                                        <div class="next-chapter-hint p-3 bg-light rounded">
                                                                            ${workflowData.storyline.next_chapter_hint}
                                                                        </div>
                                                                    </div>
                                                                ` : ''}
                                                            </div>
                                                        </div>
                                                        <div class="col-md-4">
                                                            <div class="chapter-info-section">
                                                                <h6 class="text-secondary mb-3">章节信息</h6>
                                                                <div class="chapter-info p-3 bg-light rounded">
                                                                    <div class="mb-2">
                                                                        <strong>章节号:</strong><br>
                                                                        <span class="text-muted">第${chapterNumber}章</span>
                                                                    </div>
                                                                    <div class="mb-2">
                                                                        <strong>字数:</strong><br>
                                                                        <span class="text-muted">${workflowData.storyline.word_count || '未知'}字</span>
                                                                    </div>
                                                                    <div class="mb-2">
                                                                        <strong>创建时间:</strong><br>
                                                                        <span class="text-muted">${Utils.formatDate(workflowData.storyline.created_at)}</span>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ` : `
                                                <div class="text-muted text-center py-5">
                                                    <i class="fas fa-exclamation-circle me-2"></i>
                                                    暂无故事线数据
                                                </div>
                                            `}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 评价和正文评价模块 -->
                            <div class="row mb-4">
                                <!-- 评价模块 -->
                                <div class="col-md-6">
                                    <div class="workflow-module card h-100">
                                        <div class="card-header bg-warning text-dark">
                                            <h6 class="mb-0"><i class="fas fa-star me-2"></i>故事线评价</h6>
                                        </div>
                                        <div class="card-body">
                                            ${workflowData.storylineQuality ? `
                                                <div class="quality-content">
                                                    <div class="quality-score mb-3 text-center">
                                                        <span class="badge bg-info fs-5 px-3 py-2">
                                                            综合评分: ${workflowData.storylineQuality.overall_score || '未知'}分
                                                        </span>
                                                    </div>
                                                    <div class="evaluation-details">
                                                        <div class="mb-3">
                                                            <h6 class="text-secondary">各维度评分</h6>
                                                            <div class="scores-grid">
                                                                ${workflowData.storylineQuality.scores ? Object.entries(workflowData.storylineQuality.scores).map(([key, value]) => `
                                                                    <div class="score-item d-flex justify-content-between mb-1">
                                                                        <span class="text-muted">${getScoreLabel(key)}:</span>
                                                                        <span class="badge bg-secondary">${value}分</span>
                                                                    </div>
                                                                `).join('') : ''}
                                                            </div>
                                                        </div>
                                                        
                                                        ${workflowData.storylineQuality.strengths && workflowData.storylineQuality.strengths.length > 0 ? `
                                                            <div class="strengths mb-3">
                                                                <h6 class="text-success">优点</h6>
                                                                <ul class="list-unstyled">
                                                                    ${workflowData.storylineQuality.strengths.map(strength => `<li class="mb-1"><i class="fas fa-check-circle me-2 text-success"></i>${strength}</li>`).join('')}
                                                                </ul>
                                                            </div>
                                                        ` : ''}
                                                        
                                                        ${workflowData.storylineQuality.weaknesses && workflowData.storylineQuality.weaknesses.length > 0 ? `
                                                            <div class="weaknesses">
                                                                <h6 class="text-warning">改进建议</h6>
                                                                <ul class="list-unstyled">
                                                                    ${workflowData.storylineQuality.weaknesses.map(weakness => `<li class="mb-1"><i class="fas fa-lightbulb me-2 text-warning"></i>${weakness}</li>`).join('')}
                                                                </ul>
                                                            </div>
                                                        ` : ''}
                                                    </div>
                                                </div>
                                            ` : `
                                                <div class="text-muted text-center py-3">
                                                    <i class="fas fa-exclamation-circle me-2"></i>
                                                    暂无评价数据
                                                </div>
                                            `}
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- 正文评价模块 -->
                                <div class="col-md-6">
                                    <div class="workflow-module card h-100">
                                        <div class="card-header bg-info text-white">
                                            <h6 class="mb-0"><i class="fas fa-file-alt me-2"></i>正文评价</h6>
                                        </div>
                                        <div class="card-body">
                                            ${workflowData.chapterQuality ? `
                                                <div class="chapter-quality-content">
                                                    <div class="quality-score mb-3 text-center">
                                                        <span class="badge ${workflowData.chapterQuality.overall_score >= 80 ? 'bg-success' : workflowData.chapterQuality.overall_score >= 60 ? 'bg-warning' : 'bg-danger'} fs-5 px-3 py-2">
                                                            ${chapterNumber === 1 ? '故事线质量' : '续写质量'}: ${workflowData.chapterQuality.overall_score}分
                                                        </span>
                                                    </div>
                                                    <div class="evaluation-details">
                                                        <div class="mb-3">
                                                            <h6 class="text-secondary">各维度评分</h6>
                                                            <div class="scores-grid">
                                                                ${chapterNumber === 1 ? 
                                                                    // 第一章显示故事线评分
                                                                    (workflowData.chapterQuality.scores ? Object.entries(workflowData.chapterQuality.scores).map(([key, value]) => `
                                                                        <div class="score-item d-flex justify-content-between mb-1">
                                                                            <span class="text-muted">${getScoreLabel(key)}:</span>
                                                                            <span class="badge bg-secondary">${value}分</span>
                                                                        </div>
                                                                    `).join('') : '') :
                                                                    // 续写章节显示章节评分
                                                                    (workflowData.chapterQuality.dimensions ? Object.entries(workflowData.chapterQuality.dimensions).map(([key, value]) => `
                                                                        <div class="score-item d-flex justify-content-between mb-1">
                                                                            <span class="text-muted">${getChapterScoreLabel(key)}:</span>
                                                                            <span class="badge bg-secondary">${value}分</span>
                                                                        </div>
                                                                    `).join('') : '')
                                                                }
                                                            </div>
                                                        </div>
                                                        
                                                        ${chapterNumber === 1 ? 
                                                            // 第一章显示故事线的优点和缺点
                                                            (workflowData.chapterQuality.strengths && workflowData.chapterQuality.strengths.length > 0 ? `
                                                                <div class="strengths mb-3">
                                                                    <h6 class="text-success">优点</h6>
                                                                    <ul class="list-unstyled">
                                                                        ${workflowData.chapterQuality.strengths.map(strength => `<li class="mb-1"><i class="fas fa-check-circle me-2 text-success"></i>${strength}</li>`).join('')}
                                                                    </ul>
                                                                </div>
                                                            ` : '') +
                                                            (workflowData.chapterQuality.weaknesses && workflowData.chapterQuality.weaknesses.length > 0 ? `
                                                                <div class="weaknesses">
                                                                    <h6 class="text-warning">改进建议</h6>
                                                                    <ul class="list-unstyled">
                                                                        ${workflowData.chapterQuality.weaknesses.map(weakness => `<li class="mb-1"><i class="fas fa-lightbulb me-2 text-warning"></i>${weakness}</li>`).join('')}
                                                                    </ul>
                                                                </div>
                                                            ` : '') :
                                                            // 续写章节显示改进建议
                                                            (workflowData.chapterQuality.suggestions && workflowData.chapterQuality.suggestions.length > 0 ? `
                                                                <div class="suggestions">
                                                                    <h6 class="text-info">改进建议</h6>
                                                                    <ul class="list-unstyled">
                                                                        ${workflowData.chapterQuality.suggestions.map(suggestion => `<li class="mb-1"><i class="fas fa-lightbulb me-2 text-info"></i>${suggestion}</li>`).join('')}
                                                                    </ul>
                                                                </div>
                                                            ` : '')
                                                        }
                                                    </div>
                                                </div>
                                            ` : `
                                                <div class="text-muted text-center py-3">
                                                    <i class="fas fa-exclamation-circle me-2"></i>
                                                    暂无正文评价数据
                                                </div>
                                            `}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除已存在的模态框
    const existingModal = document.getElementById('chapterWorkflowModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新模态框到页面
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('chapterWorkflowModal'));
    modal.show();
};

// 获取步骤显示名称
const getStepDisplayName = (stepKey) => {
    const stepNames = {
        'tag_selection': '标签选择',
        'character_creation': '人物创建',
        'storyline_generation': '故事线生成',
        'knowledge_graph_creation': '知识图谱创建',
        'chapter_writing': '章节写作'
    };
    return stepNames[stepKey] || stepKey;
};

// 获取步骤描述
const getStepDescription = (stepKey) => {
    const stepDescriptions = {
        'tag_selection': '选择小说的类型、风格和主题标签',
        'character_creation': '创建主要角色和配角',
        'storyline_generation': '生成故事大纲和情节发展',
        'knowledge_graph_creation': '构建故事世界知识图谱',
        'chapter_writing': '根据大纲创作具体章节内容'
    };
    return stepDescriptions[stepKey] || '工作流程步骤';
};

// 获取状态显示名称
const getStatusDisplayName = (status) => {
    const statusNames = {
        'completed': '已完成',
        'in_progress': '进行中',
        'pending': '待处理',
        'failed': '失败'
    };
    return statusNames[status] || status;
};

// 获取评分标签的中文名称
const getScoreLabel = (key) => {
    const labels = {
        'coherence': '连贯性',
        'coordination': '协调性', 
        'structure': '结构',
        'conflict': '冲突',
        'innovation': '创新性'
    };
    return labels[key] || key;
};

// 获取章节评分标签的中文名称
const getChapterScoreLabel = (key) => {
    const labels = {
        'character_consistency': '人物一致性',
        'plot_continuity': '情节连续性',
        'world_consistency': '世界观一致性',
        'foreshadowing_continuity': '伏笔连续性',
        'style_consistency': '风格一致性'
    };
    return labels[key] || key;
};

// 加载工作流模块数据
const loadWorkflowModules = async (novelId, chapterNumber) => {
    const modules = {};
    
    // 1. 故事线 - 根据章节号获取对应的章节数据
    try {
        const chapterResponse = await Utils.apiRequest(`/novels/${novelId}/chapters`);
        if (chapterResponse.success && chapterResponse.data) {
            // 查找对应章节的数据
            const targetChapter = chapterResponse.data.find(chapter => chapter.chapter_number === chapterNumber);
            if (targetChapter) {
                modules.storyline = {
                    chapter_title: targetChapter.title,
                    chapter_summary: targetChapter.summary,
                    key_events: targetChapter.key_events,
                    character_development: targetChapter.character_development,
                    foreshadowing: targetChapter.foreshadowing,
                    next_chapter_hint: targetChapter.next_chapter_hint,
                    word_count: targetChapter.word_count
                };
            } else {
                modules.storyline = null;
            }
        } else {
            modules.storyline = null;
        }
    } catch (error) {
        modules.storyline = null;
    }
    
    // 2. 评价（原始故事线质量评估）
    try {
        const storylineQualityResponse = await Utils.apiRequest(`/novels/${novelId}/data/storyline_quality_assessment`);
        modules.storylineQuality = storylineQualityResponse.success ? storylineQualityResponse.data : null;
    } catch (error) {
        modules.storylineQuality = null;
    }
    
    // 3. 正文评价（根据章节号显示不同的评价）
    try {
        if (chapterNumber === 1) {
            // 第一章显示原始故事线评价
            const storylineQualityResponse = await Utils.apiRequest(`/novels/${novelId}/data/storyline_quality_assessment`);
            modules.chapterQuality = storylineQualityResponse.success ? storylineQualityResponse.data : null;
        } else {
            // 续写章节显示续写章节评价
            const chapterQualityResponse = await Utils.apiRequest(`/novels/${novelId}/data/continuation_chapter_quality_assessment`);
            modules.chapterQuality = chapterQualityResponse.success ? chapterQualityResponse.data : null;
        }
    } catch (error) {
        modules.chapterQuality = null;
    }
    
    
    return modules;
};


// 全局函数
window.toggleContinuationEditMode = ContinuationEditModeManager.toggleEditMode;
window.saveContinuationStorylineContent = ContinuationContentSaveManager.saveStorylineContent;

// 删除章节功能
window.deleteChapter = async (novelId, chapterNumber, chapterTitle) => {
    try {
        // 显示确认对话框
        const confirmed = await showDeleteConfirmDialog(
            '删除章节',
            `确定要删除 "${chapterTitle}" 吗？此操作不可撤销。`,
            'danger'
        );
        
        if (!confirmed) {
            return;
        }
        
        Utils.showLoading('正在删除章节...');
        
        // 调用删除API
        const response = await Utils.apiRequest(`/novels/${novelId}/chapters/${chapterNumber}`, {
            method: 'DELETE'
        });
        
        if (response.success) {
            Utils.showMessage(`章节 "${chapterTitle}" 删除成功！`, 'success');
            
            // 刷新章节列表
            showChapterSelectionForEdit();
        } else {
            throw new Error(response.error || '删除章节失败');
        }
        
    } catch (error) {
        Utils.showMessage('删除章节失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 删除小说功能
window.deleteNovel = async (novelId, novelTitle) => {
    try {
        // 显示确认对话框
        const confirmed = await showDeleteConfirmDialog(
            '删除小说',
            `确定要删除小说 "${novelTitle}" 吗？这将删除所有章节和相关数据，此操作不可撤销！`,
            'danger'
        );
        
        if (!confirmed) {
            return;
        }
        
        Utils.showLoading('正在删除小说...');
        
        // 调用删除API
        const response = await Utils.apiRequest(`/novels/${novelId}`, {
            method: 'DELETE'
        });
        
        if (response.success) {
            Utils.showMessage(`小说 "${novelTitle}" 删除成功！`, 'success');
            
            // 返回小说列表
            Navigation.goToNovelList();
            loadNovelList();
        } else {
            throw new Error(response.error || '删除小说失败');
        }
        
    } catch (error) {
        Utils.showMessage('删除小说失败: ' + error.message, 'danger');
    } finally {
        Utils.hideLoading();
    }
};

// 显示删除确认对话框
const showDeleteConfirmDialog = (title, message, type = 'warning') => {
    return new Promise((resolve) => {
        const modalHtml = `
            <div class="modal fade" id="deleteConfirmModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-${type} text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-exclamation-triangle me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="mb-0">${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-${type}" id="confirmDeleteBtn">确认删除</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 移除现有模态框
        const existingModal = document.getElementById('deleteConfirmModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        
        // 绑定确认按钮事件
        document.getElementById('confirmDeleteBtn').addEventListener('click', () => {
            modal.hide();
            resolve(true);
        });
        
        // 绑定取消事件
        document.getElementById('deleteConfirmModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('deleteConfirmModal').remove();
            resolve(false);
        });
        
        modal.show();
    });
};

// 全局导航函数（供HTML onclick调用）
window.goToHome = Navigation.goToHome;
window.goToNovelList = Navigation.goToNovelList;
window.goToContinuationNovelList = Navigation.goToContinuationNovelList;

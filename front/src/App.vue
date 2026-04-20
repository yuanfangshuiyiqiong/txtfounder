<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Search, Refresh, Plus, Document, InfoFilled, QuestionFilled, CopyDocument, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'

const query = ref('')
const results = ref([])
const loading = ref(false)
const topK = ref(5)
const activeTab = ref('search')
const showReadme = ref(false)
const readmeContent = ref('')
const fileInput = ref(null)

const triggerUpload = () => {
  fileInput.value.click()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  loading.value = true
  try {
    const response = await axios.post('http://localhost:8000/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    ElMessage.success(response.data.message)
    // 上传成功后清空文件输入，以便下次上传同一文件
    event.target.value = ''
  } catch (error) {
    ElMessage.error('文件上传失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const fetchReadme = async () => {
  try {
    const response = await axios.get('http://localhost:8000/readme')
    readmeContent.value = marked.parse(response.data.content)
    showReadme.value = true
  } catch (error) {
    ElMessage.error('获取教程失败：' + (error.response?.data?.detail || error.message))
  }
}

const search = async () => {
  if (!query.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }

  loading.value = true
  try {
    const response = await axios.post('http://localhost:8000/search', {
      query: query.value,
      top_k: topK.value
    })
    results.value = response.data
    if (results.value.length === 0) {
      ElMessage.info('没有找到相关结果')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('搜索出错：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const rebuildIndex = async () => {
  try {
    await ElMessageBox.confirm('确定要重新构建整个索引吗？这可能需要一些时间。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    loading.value = true
    const response = await axios.post('http://localhost:8000/rebuild')
    ElMessage.success(response.data.message)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重构索引出错：' + (error.response?.data?.detail || error.message))
    }
  } finally {
    loading.value = false
  }
}

const updateIndex = async () => {
  loading.value = true
  try {
    const response = await axios.post('http://localhost:8000/update')
    ElMessage.success(response.data.message)
  } catch (error) {
    ElMessage.error('更新索引出错：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const formatScore = (score) => {
  return (score * 100).toFixed(1) + '%'
}

const getSimilarityClass = (score) => {
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

const truncateFileName = (name) => {
  if (name.length > 50) {
    return name.substring(0, 47) + '...'
  }
  return name
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('文件路径已复制到剪贴板')
  }, (err) => {
    ElMessage.error('复制失败: ' + err)
  })
}

onMounted(() => {
  // 可以在这里检查后端是否运行
})
</script>

<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo-icon">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <span class="logo-text">文档搜索</span>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section">
          <div class="nav-section-title">数据管理</div>
          <el-button class="nav-btn" :icon="Upload" @click="triggerUpload" :loading="loading" plain>
            上传文件
          </el-button>
          <el-button class="nav-btn" :icon="Refresh" @click="updateIndex" :loading="loading" plain>
            增量更新
          </el-button>
          <el-button class="nav-btn danger" :icon="Refresh" @click="rebuildIndex" :loading="loading" plain>
            重建索引
          </el-button>
        </div>

        <div class="nav-section">
          <div class="nav-section-title">系统</div>
          <el-button class="nav-btn" :icon="QuestionFilled" @click="fetchReadme" plain>
            使用教程
          </el-button>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="system-status">
          <span class="status-dot"></span>
          <span class="status-text">系统就绪</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-wrapper">
        <!-- 搜索区域 -->
        <div class="search-section">
          <h1 class="page-title">智能文档搜索</h1>
          <p class="page-desc">基于语义理解的文档检索系统，快速找到你需要的内容</p>

          <el-input
            v-model="query"
            placeholder="输入关键词或问题，开始智能搜索..."
            class="search-input"
            @keyup.enter="search"
            size="large"
          >
            <template #append>
              <el-button :icon="Search" @click="search" :loading="loading">搜索</el-button>
            </template>
          </el-input>

          <div class="search-options">
            <span>返回结果数量</span>
            <el-slider v-model="topK" :min="1" :max="100" style="width: 200px;" />
            <span class="topk-value">{{ topK }}</span>
          </div>
        </div>

        <!-- 结果区域 -->
        <div class="results-section" v-loading="loading">
          <el-empty v-if="results.length === 0 && !loading" description="暂无搜索结果" />

          <div v-else class="result-list">
            <div class="results-header">
              <span class="results-count">找到 {{ results.length }} 条相关结果</span>
            </div>

            <el-card v-for="(item, index) in results" :key="index" class="result-item" shadow="hover">
              <template #header>
                <div class="result-header">
                  <span class="file-name">
                    <el-tag size="small">#{{ item.rank }}</el-tag>
                    {{ truncateFileName(item.file_name) }}
                  </span>
                  <span :class="['similarity-tag', getSimilarityClass(item.similarity_score)]">
                    {{ formatScore(item.similarity_score) }}
                  </span>
                </div>
              </template>
              <div class="result-content">
                {{ item.content }}
              </div>
              <div class="result-footer">
                <el-button
                  :icon="CopyDocument"
                  @click="copyToClipboard(item.file_path)"
                  size="small"
                >
                  复制路径
                </el-button>
                <span class="file-path-display">{{ item.file_path }}</span>
              </div>
            </el-card>
          </div>
        </div>
      </div>
    </main>

    <el-dialog
      v-model="showReadme"
      title="使用教程"
      width="60%"
      destroy-on-close
    >
      <div class="markdown-content" v-html="readmeContent"></div>
    </el-dialog>

    <input type="file" ref="fileInput" @change="handleFileUpload" style="display: none" />
  </div>
</template>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
</style>

<style>
/* 全局 CSS 变量 */
:root {
  --bg-primary: #F9FAFB;
  --bg-card: #FFFFFF;
  --bg-sidebar: linear-gradient(180deg, #1E3A5F 0%, #243B55 40%, #1E3A5F 100%);
  --bg-sidebar-hover: rgba(255, 255, 255, 0.12);
  --bg-sidebar-active: rgba(255, 255, 255, 0.18);
  --text-primary: #1F2937;
  --text-secondary: #6B7280;
  --text-muted: #9CA3AF;
  --text-sidebar: rgba(255, 255, 255, 0.88);
  --text-sidebar-muted: rgba(255, 255, 255, 0.5);
  --border-color: #E5E7EB;
  --brand-primary: #1E3A5F;
  --brand-secondary: #2D5A87;
  --brand-gradient: linear-gradient(135deg, #1E3A5F 0%, #3D6B99 100%);
  --slider-track: #CBD5E1;
  --slider-fill: #2D5A87;
  --success: #059669;
  --warning: #D97706;
  --danger: #DC2626;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 12px -2px rgba(0, 0, 0, 0.06), 0 2px 6px -2px rgba(0, 0, 0, 0.03);
  --shadow-lg: 0 12px 24px -4px rgba(0, 0, 0, 0.07), 0 6px 12px -4px rgba(0, 0, 0, 0.03);
  --radius-sm: 12px;
  --radius-md: 16px;
  --radius-lg: 20px;
  --sidebar-width: 240px;
}

/* 整体布局 */
.app-layout {
  display: flex;
  min-height: 100vh;
  background-color: var(--bg-primary);
}

/* 侧边栏 */
.sidebar {
  width: var(--sidebar-width);
  min-height: 100vh;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
}

.sidebar-header {
  padding: 28px 24px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar .logo-icon {
  width: 42px;
  height: 42px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(8px);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: white;
  letter-spacing: -0.01em;
}

.sidebar-nav {
  flex: 1;
  padding: 24px 16px;
  overflow-y: auto;
}

.nav-section {
  margin-bottom: 32px;
}

.nav-section-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-sidebar-muted);
  padding: 0 12px;
  margin-bottom: 12px;
}

.nav-btn {
  width: 100%;
  justify-content: flex-start;
  padding: 13px 16px;
  margin-bottom: 6px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-sidebar);
  font-weight: 500;
  font-size: 14px;
  transition: all 0.2s ease;
  letter-spacing: 0.01em;
}

.nav-btn:hover {
  background: var(--bg-sidebar-hover);
  color: white;
}

.nav-btn.is-active {
  background: var(--bg-sidebar-active);
  color: white;
}

.nav-btn.danger {
  color: #FCA5A5;
}

.nav-btn.danger:hover {
  background: rgba(220, 38, 38, 0.15);
  color: #FCA5A5;
}

.sidebar-footer {
  padding: 20px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.system-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

.status-text {
  font-size: 13px;
  color: var(--text-sidebar-muted);
}

/* 主内容区 */
.main-content {
  flex: 1;
  margin-left: var(--sidebar-width);
  min-height: 100vh;
}

.content-wrapper {
  max-width: 1000px;
  margin: 0 auto;
  padding: 48px 48px;
}

/* 搜索区域 */
.search-section {
  background: var(--bg-card);
  padding: 36px 40px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  margin-bottom: 48px;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 12px;
  letter-spacing: -0.02em;
}

.page-desc {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0 0 32px;
  line-height: 1.6;
}

.search-input {
  margin-bottom: 24px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  padding: 8px 20px;
  box-shadow: var(--shadow-md) !important;
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.search-input :deep(.el-input__wrapper:hover),
.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--brand-secondary);
  box-shadow: var(--shadow-lg) !important;
}

.search-input :deep(.el-input__inner) {
  font-size: 16px;
  height: 52px;
}

.search-input :deep(.el-input-group__append) {
  border-radius: var(--radius-lg);
  background: var(--brand-gradient);
  border: none;
  color: white;
  font-weight: 500;
  font-size: 15px;
  padding: 0 28px;
  margin: 4px;
}

.search-input :deep(.el-button) {
  background: transparent;
  border: none;
  color: white;
}

.search-options {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
  color: var(--text-secondary);
}

.search-options :deep(.el-slider__runway) {
  background-color: var(--slider-track);
  height: 5px;
  border-radius: 3px;
}

.search-options :deep(.el-slider__bar) {
  background: var(--slider-fill);
  height: 5px;
  border-radius: 3px;
}

.search-options :deep(.el-slider__button-wrapper) {
  top: -8px;
}

.search-options :deep(.el-slider__button) {
  border: none;
  width: 14px;
  height: 14px;
  background: var(--brand-primary);
  box-shadow: 0 2px 6px rgba(30, 58, 95, 0.35);
}

.topk-value {
  min-width: 32px;
  text-align: center;
  font-weight: 600;
  color: var(--brand-primary);
}

/* 结果区域 */
.results-section {
  min-height: 400px;
}

.results-header {
  margin-bottom: 24px;
}

.results-count {
  font-size: 14px;
  color: var(--text-muted);
  font-weight: 500;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.result-item {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(0, 0, 0, 0.04);
  transition: all 0.25s ease;
  overflow: hidden;
}

.result-item:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.result-item :deep(.el-card__header) {
  padding: 18px 24px;
  background: linear-gradient(to bottom, #FAFBFC, #F9FAFB);
  border-bottom: 1px solid var(--border-color);
}

.result-item :deep(.el-card__body) {
  padding: 24px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.file-name {
  font-weight: 500;
  font-size: 15px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.file-name .el-tag {
  border-radius: 6px;
  font-weight: 600;
  background: var(--bg-primary);
  border: none;
  color: var(--text-secondary);
}

.similarity-tag {
  border-radius: 6px;
  font-weight: 500;
  padding: 6px 12px;
  border: none;
  flex-shrink: 0;
}

.similarity-tag.high {
  background: linear-gradient(135deg, #D1FAE5, #A7F3D0);
  color: #065F46;
}

.similarity-tag.medium {
  background: linear-gradient(135deg, #FEF3C7, #FDE68A);
  color: #92400E;
}

.similarity-tag.low {
  background: linear-gradient(135deg, #F3F4F6, #E5E7EB);
  color: #6B7280;
}

.result-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  white-space: pre-wrap;
  background: var(--bg-primary);
  padding: 20px;
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
}

.result-footer {
  display: flex;
  align-items: center;
  gap: 16px;
}

.result-footer .el-button {
  border-radius: var(--radius-sm);
  font-weight: 500;
  border-color: var(--border-color);
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.result-footer .el-button:hover {
  border-color: var(--brand-secondary);
  color: var(--brand-primary);
  background: var(--bg-primary);
}

.file-path-display {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--text-muted);
  font-family: "SF Mono", Monaco, monospace;
}

/* 空状态 */
.el-empty {
  padding: 80px 20px;
}

.el-empty :deep(.el-empty__image) {
  width: 120px;
  height: 120px;
  opacity: 0.6;
}

.el-empty :deep(.el-empty__description p) {
  color: var(--text-muted);
  font-size: 15px;
  margin-top: 16px;
}

/* Dialog 样式 */
.el-dialog {
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.el-dialog :deep(.el-dialog__header) {
  padding: 24px 32px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  margin: 0;
}

.el-dialog :deep(.el-dialog__title) {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 18px;
}

.el-dialog :deep(.el-dialog__body) {
  padding: 32px;
}

.el-dialog :deep(.el-dialog__headerbtn) {
  width: 36px;
  height: 36px;
  top: 20px;
  right: 20px;
}

.el-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  font-size: 20px;
  color: var(--text-muted);
}

/* Markdown 内容 */
.markdown-content {
  line-height: 1.8;
  color: var(--text-secondary);
}

.markdown-content :deep(h1) {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 32px 0 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--border-color);
}

.markdown-content :deep(h2) {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 28px 0 16px;
}

.markdown-content :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 24px 0 12px;
}

.markdown-content :deep(p) {
  margin: 16px 0;
}

.markdown-content :deep(code) {
  background-color: var(--bg-primary);
  padding: 3px 8px;
  border-radius: 4px;
  font-family: "SF Mono", Monaco, monospace;
  font-size: 13px;
  color: var(--brand-primary);
}

.markdown-content :deep(pre) {
  background-color: var(--bg-primary);
  padding: 20px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: 20px 0;
  border: 1px solid var(--border-color);
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text-secondary);
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 16px 0;
  padding-left: 24px;
}

.markdown-content :deep(li) {
  margin: 8px 0;
}

.markdown-content :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-sm);
}

/* 加载动画 */
.el-loading-mask {
  background-color: rgba(249, 250, 251, 0.9);
}

.el-loading-spinner .circular {
  width: 42px;
  height: 42px;
}

.el-loading-spinner .path {
  stroke: var(--brand-primary);
}
</style>

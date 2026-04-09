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
  <div class="app-container">
    <el-header class="header">
      <div class="logo">
        <el-icon :size="24"><Document /></el-icon>
        <span class="title">文件搜索系统</span>
      </div>
      <div class="actions">
        <el-button :icon="QuestionFilled" @click="fetchReadme" circle style="margin-right: 15px;"></el-button>
        <el-button type="success" :icon="Upload" @click="triggerUpload" :loading="loading">添加文件</el-button>
        <el-button type="primary" :icon="Refresh" @click="updateIndex" :loading="loading">增量更新</el-button>
        <el-button type="danger" :icon="Refresh" @click="rebuildIndex" :loading="loading">重新构建</el-button>
      </div>
    </el-header>

    <el-main class="main">
      <!-- ... existing search-section ... -->
      <div class="search-section">
        <el-input
          v-model="query"
          placeholder="请输入您想查询的操作手册内容..."
          class="search-input"
          @keyup.enter="search"
          size="large"
        >
          <template #append>
            <el-button :icon="Search" @click="search" :loading="loading">搜索</el-button>
          </template>
        </el-input>
        
        <div class="search-options">
          <span>返回结果数量: </span>
          <el-slider v-model="topK" :min="1" :max="100" style="width: 200px; margin-left: 10px;" />
          <span style="margin-left: 10px;">{{ topK }}</span>
        </div>
      </div>

      <div class="results-section" v-loading="loading">
        <el-empty v-if="results.length === 0 && !loading" description="暂无搜索结果" />
        
        <div v-else class="result-list">
          <el-card v-for="(item, index) in results" :key="index" class="result-item" shadow="hover">
            <template #header>
              <div class="result-header">
                <span class="file-name">
                  <el-tag size="small" type="info">#{{ item.rank }}</el-tag>
                  {{ item.file_name }}
                </span>
                <el-tag :type="item.similarity_score > 0.8 ? 'success' : 'warning'">
                  相似度: {{ formatScore(item.similarity_score) }}
                </el-tag>
              </div>
            </template>
            <div class="result-content">
              {{ item.content }}
            </div>
            <div class="result-footer">
              <el-button 
                type="primary" 
                :icon="CopyDocument" 
                @click="copyToClipboard(item.file_path)"
                size="small"
                plain
              >
                复制文件路径
              </el-button>
              <span class="file-path-display">{{ item.file_path }}</span>
            </div>
          </el-card>
        </div>
      </div>
    </el-main>

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
}
</style>

<style scoped>
.app-container {
  width: 80%;
  margin: 0 auto;
  min-height: 100vh;
  background-color: #f5f7fa;
  display: flex;
  flex-direction: column;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
}

.main {
  flex: 1;
  padding: 30px 20px;
}

.search-section {
  margin-bottom: 30px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.search-input {
  margin-bottom: 15px;
}

.search-options {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #606266;
}

.results-section {
  min-height: 300px;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.result-item {
  border-radius: 8px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-name {
  font-weight: bold;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.result-content {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  white-space: pre-wrap;
}

.result-footer {
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px dashed #ebeef5;
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-path-display {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #909399;
}

.markdown-content {
  line-height: 1.6;
  color: #303133;
}

.markdown-content :deep(h1), 
.markdown-content :deep(h2), 
.markdown-content :deep(h3) {
  margin-top: 20px;
  margin-bottom: 10px;
}

.markdown-content :deep(code) {
  background-color: #f0f2f5;
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
}

.markdown-content :deep(pre) {
  background-color: #f0f2f5;
  padding: 15px;
  border-radius: 8px;
  overflow-x: auto;
}

.markdown-content :deep(img) {
  max-width: 100%;
}
</style>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
</style>

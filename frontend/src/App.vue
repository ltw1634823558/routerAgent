<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <el-container>
        <el-aside width="260px" class="sidebar">
          <div class="logo">
            <div class="logo-icon">
              <span class="robot">🤖</span>
            </div>
            <h1>RouterAgent</h1>
            <p class="subtitle">智能体管理平台</p>
          </div>
          <el-menu
            :default-active="activeMenu"
            router
            class="sidebar-menu"
          >
            <el-menu-item index="/model" class="menu-item-model">
              <template #title>
                <div class="menu-content">
                  <el-icon class="menu-icon"><Setting /></el-icon>
                  <span>模型配置</span>
                </div>
                <div class="menu-indicator"></div>
              </template>
            </el-menu-item>
            <el-menu-item index="/search" class="menu-item-search">
              <template #title>
                <div class="menu-content">
                  <el-icon class="menu-icon"><Search /></el-icon>
                  <span>搜集 Agent</span>
                </div>
                <div class="menu-indicator"></div>
              </template>
            </el-menu-item>
            <el-menu-item index="/prompt" class="menu-item-prompt">
              <template #title>
                <div class="menu-content">
                  <el-icon class="menu-icon"><EditPen /></el-icon>
                  <span>提示词优化</span>
                </div>
                <div class="menu-indicator"></div>
              </template>
            </el-menu-item>
            <el-menu-item index="/quiz" class="menu-item-quiz">
              <template #title>
                <div class="menu-content">
                  <el-icon class="menu-icon"><Document /></el-icon>
                  <span>问答 Agent</span>
                </div>
                <div class="menu-indicator"></div>
              </template>
            </el-menu-item>
            <el-menu-item index="/knowledge" class="menu-item-knowledge">
              <template #title>
                <div class="menu-content">
                  <el-icon class="menu-icon"><FolderOpened /></el-icon>
                  <span>知识库</span>
                </div>
                <div class="menu-indicator"></div>
              </template>
            </el-menu-item>
          </el-menu>
          <div class="sidebar-footer">
            <div class="status-dot"></div>
            <span>系统运行正常</span>
          </div>
        </el-aside>

        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar {
  background: linear-gradient(180deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.3);
  position: relative;
  overflow: hidden;
}

.sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  pointer-events: none;
}

.logo {
  padding: 28px 20px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 1;
}

.logo-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.robot {
  font-size: 32px;
}

.logo h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 1px;
}

.subtitle {
  margin: 8px 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 2px;
}

.sidebar-menu {
  border: none;
  background: transparent;
  flex: 1;
  padding: 16px 12px;
  position: relative;
  z-index: 1;
}

.sidebar-menu .el-menu-item {
  color: rgba(255, 255, 255, 0.7);
  height: 52px;
  line-height: 52px;
  margin: 4px 0;
  border-radius: 12px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.sidebar-menu .el-menu-item .menu-content {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  z-index: 1;
}

.sidebar-menu .el-menu-item .menu-icon {
  font-size: 18px;
  transition: transform 0.3s ease;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  transform: translateX(4px);
}

.sidebar-menu .el-menu-item:hover .menu-icon {
  transform: scale(1.1);
}

.sidebar-menu .el-menu-item.is-active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%);
  color: #fff;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.sidebar-menu .el-menu-item.is-active .menu-icon {
  color: #a78bfa;
}

/* 不同菜单项的活跃颜色 */
.menu-item-model.is-active { background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(5, 150, 105, 0.3) 100%); }
.menu-item-model.is-active .menu-icon { color: #10b981; }

.menu-item-search.is-active { background: linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(37, 99, 235, 0.3) 100%); }
.menu-item-search.is-active .menu-icon { color: #3b82f6; }

.menu-item-prompt.is-active { background: linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(139, 92, 246, 0.3) 100%); }
.menu-item-prompt.is-active .menu-icon { color: #a855f7; }

.menu-item-quiz.is-active { background: linear-gradient(135deg, rgba(249, 115, 22, 0.3) 0%, rgba(234, 88, 12, 0.3) 100%); }
.menu-item-quiz.is-active .menu-icon { color: #f97316; }

.menu-item-knowledge.is-active { background: linear-gradient(135deg, rgba(236, 72, 153, 0.3) 0%, rgba(219, 39, 119, 0.3) 100%); }
.menu-item-knowledge.is-active .menu-icon { color: #ec4899; }

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  position: relative;
  z-index: 1;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  50% { opacity: 0.8; box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
}

.main-content {
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  padding: 24px;
  height: 100vh;
  overflow-y: auto;
  position: relative;
}

.main-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 20% 80%, rgba(102, 126, 234, 0.05) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(118, 75, 162, 0.05) 0%, transparent 50%);
  pointer-events: none;
}
</style>

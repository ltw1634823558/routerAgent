<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <el-container>
        <el-aside width="240px" class="sidebar">
          <div class="logo">
            <h1>🤖 RouterAgent</h1>
          </div>
          <el-menu
            :default-active="activeMenu"
            router
            class="sidebar-menu"
          >
            <el-menu-item index="/model">
              <el-icon><Setting /></el-icon>
              <span>模型配置</span>
            </el-menu-item>
            <el-menu-item index="/search">
              <el-icon><Search /></el-icon>
              <span>搜集 Agent</span>
            </el-menu-item>
            <el-menu-item index="/prompt">
              <el-icon><EditPen /></el-icon>
              <span>提示词优化</span>
            </el-menu-item>
            <el-menu-item index="/quiz">
              <el-icon><Document /></el-icon>
              <span>问答 Agent</span>
            </el-menu-item>
            <el-menu-item index="/knowledge">
              <el-icon><FolderOpened /></el-icon>
              <span>知识库</span>
            </el-menu-item>
          </el-menu>
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
}

.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
}

.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo h1 {
  margin: 0;
  font-size: 20px;
  color: #fff;
}

.sidebar-menu {
  border: none;
  background: transparent;
}

.sidebar-menu .el-menu-item {
  color: rgba(255, 255, 255, 0.8);
}

.sidebar-menu .el-menu-item:hover,
.sidebar-menu .el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.1);
  color: #409eff;
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
  height: 100vh;
  overflow-y: auto;
}
</style>

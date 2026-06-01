<script setup lang="ts">
import { Aim, MagicStick, Promotion } from '@element-plus/icons-vue';
import { RouterView } from 'vue-router';
</script>

<template>
  <div class="auth-shell">
    <aside class="hero">
      <div class="brand">
        <div class="logo">
          <el-icon :size="22" color="#fff"><Aim /></el-icon>
        </div>
        <div>
          <strong>寻迹</strong>
          <small>Xunji · Campus Lost & Found</small>
        </div>
      </div>
      <div class="hero-copy">
        <span class="eyebrow">Welcome</span>
        <h1>让每一件丢失的物品<br />都能找到回家的路</h1>
        <p>实名校园社区 · 智能匹配 · 闭环交接</p>
      </div>
      <ul class="bullets">
        <li><el-icon><Promotion /></el-icon><span>三步完成发布与认领</span></li>
        <li><el-icon><MagicStick /></el-icon><span>AI 自动匹配相似物品</span></li>
        <li><el-icon><Aim /></el-icon><span>信誉分体系守护交接安全</span></li>
      </ul>
      <div class="footnote">© 2026 寻迹团队 · 软件工程课程项目</div>
    </aside>

    <main class="form-area">
      <RouterView />
    </main>
  </div>
</template>

<style scoped lang="scss">
.auth-shell {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
  background: var(--xunji-bg);
}

.hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 48px;
  color: #fff;
  background: var(--xunji-hero);
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    inset: -40% -10% auto auto;
    width: 480px;
    height: 480px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.18), transparent 70%);
    pointer-events: none;
  }
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;

  .logo {
    width: 44px;
    height: 44px;
    display: grid;
    place-items: center;
    background: rgba(255, 255, 255, 0.16);
    border-radius: 14px;
    backdrop-filter: blur(8px);
  }

  strong {
    display: block;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }

  small {
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
  }
}

.hero-copy {
  position: relative;

  .eyebrow {
    display: inline-block;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.14);
    border-radius: 999px;
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
  }

  h1 {
    margin: 18px 0 12px;
    font-size: 36px;
    line-height: 1.25;
    font-weight: 700;
  }

  p {
    color: rgba(255, 255, 255, 0.85);
    font-size: 14px;
  }
}

.bullets {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 14px;
  position: relative;

  li {
    display: flex;
    align-items: center;
    gap: 12px;
    color: rgba(255, 255, 255, 0.92);
    font-size: 14px;

    .el-icon {
      width: 32px;
      height: 32px;
      display: grid;
      place-items: center;
      background: rgba(255, 255, 255, 0.16);
      border-radius: 10px;
    }
  }
}

.footnote {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  position: relative;
}

.form-area {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

@media (max-width: 960px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }
  .hero {
    padding: 28px;

    .hero-copy h1 {
      font-size: 28px;
    }
  }
  .form-area {
    padding: 16px;
  }
}
</style>

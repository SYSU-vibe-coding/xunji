<script setup lang="ts">
import { Aim, ChatLineRound, Lock, Medal } from '@element-plus/icons-vue';
import { RouterView } from 'vue-router';
</script>

<template>
  <div class="auth-shell">
    <aside class="hero">
      <div class="brand">
        <div class="logo"><el-icon :size="22" color="#fff"><Aim /></el-icon></div>
        <div>
          <strong>寻迹后台</strong>
          <small>Admin Console</small>
        </div>
      </div>
      <div class="copy">
        <span class="eyebrow">Operations</span>
        <h1>统一处理认证、内容、举报与公告</h1>
        <p>构建一个可信赖的校园失物招领协作平台</p>
      </div>
      <ul class="bullets">
        <li><el-icon><Medal /></el-icon><span>实名身份审批</span></li>
        <li><el-icon><ChatLineRound /></el-icon><span>内容质量治理</span></li>
        <li><el-icon><Lock /></el-icon><span>风险事件复核</span></li>
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
  padding: 48px;
  color: #fff;
  background: linear-gradient(135deg, #0c2727 0%, #0d4f4f 50%, #5b21b6 100%);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    inset: -40% -10% auto auto;
    width: 480px;
    height: 480px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.16), transparent 70%);
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
    background: rgba(255, 255, 255, 0.18);
    border-radius: 14px;
  }
  strong {
    display: block;
    font-weight: 700;
    font-size: 18px;
  }
  small {
    color: rgba(255, 255, 255, 0.7);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
}

.copy {
  position: relative;
  .eyebrow {
    display: inline-block;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.16);
    border-radius: 999px;
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
  }
  h1 {
    margin: 18px 0 12px;
    font-size: 32px;
    line-height: 1.3;
  }
  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.84);
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
  position: relative;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
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
    .copy h1 {
      font-size: 24px;
    }
  }
}
</style>

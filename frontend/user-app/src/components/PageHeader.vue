<script setup lang="ts">
import { useRouter } from 'vue-router';
import { ArrowLeft } from '@element-plus/icons-vue';

const props = withDefaults(
  defineProps<{
    /** 上方小标题（英文/分类提示）；为空则不渲染 */
    eyebrow?: string;
    /** 主标题 */
    title: string;
    /** 副标题描述 */
    description?: string;
    /** 是否显示返回按钮，默认 true */
    showBack?: boolean;
    /** 无 history 时返回的 fallback 路径，默认 / */
    backFallback?: string;
  }>(),
  { showBack: true, backFallback: '/' },
);

const router = useRouter();

function goBack() {
  // history 长度 > 1 才有上一步可退；否则去 fallback
  if (window.history.length > 1) {
    router.back();
  } else {
    void router.push(props.backFallback);
  }
}
</script>

<template>
  <header class="page-header">
    <button
      v-if="showBack"
      type="button"
      class="back-btn"
      aria-label="返回"
      @click="goBack"
    >
      <el-icon :size="18"><ArrowLeft /></el-icon>
      <span>返回</span>
    </button>
    <div class="text">
      <span v-if="eyebrow" class="eyebrow">{{ eyebrow }}</span>
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
  </header>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.back-btn {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px 6px 8px;
  background: var(--xunji-surface);
  border: 1px solid var(--xunji-border);
  border-radius: 999px;
  color: var(--xunji-text);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  &:hover {
    background: rgba(13, 79, 79, 0.06);
    border-color: rgba(13, 79, 79, 0.3);
  }

  &:active {
    background: rgba(13, 79, 79, 0.1);
  }
}

.text {
  .eyebrow {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  h1 {
    margin: 6px 0 4px;
    font-size: 22px;
  }

  p {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}

@media (max-width: 720px) {
  .text h1 {
    font-size: 19px;
  }
  .text p {
    font-size: 12px;
  }
}
</style>

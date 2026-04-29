<script setup lang="ts">
import { Box } from '@element-plus/icons-vue';

withDefaults(
  defineProps<{
    title?: string;
    description?: string;
    actionText?: string;
  }>(),
  { title: '暂无数据', description: '', actionText: '' },
);

defineEmits<{ action: [] }>();
</script>

<template>
  <div class="xunji-empty">
    <el-icon :size="40" color="var(--el-text-color-placeholder)">
      <slot name="icon"><Box /></slot>
    </el-icon>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <el-button v-if="actionText" type="primary" link @click="$emit('action')">
      {{ actionText }}
    </el-button>
  </div>
</template>

<style scoped lang="scss">
.xunji-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 16px;
  color: var(--xunji-text-muted);

  strong {
    color: var(--xunji-text);
    font-size: 15px;
    font-weight: 600;
  }

  p {
    margin: 0;
    font-size: 13px;
  }
}
</style>

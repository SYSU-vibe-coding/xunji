<script setup lang="ts">
import AnnouncementPanel from '@/components/AnnouncementPanel.vue';
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="eyebrow">Campus Bulletin</span>
      <h1>校园公告</h1>
      <p>查看平台维护、失物集中处理和校园服务动态</p>
    </header>
    <AnnouncementPanel />
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  padding: 20px 22px;
  color: #fff;
  border-radius: 16px;
  background: linear-gradient(110deg, rgba(13, 79, 79, 0.96), rgba(20, 184, 166, 0.78));
  .eyebrow {
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    opacity: 0.72;
  }
  h1 {
    margin: 7px 0 5px;
    font-size: 24px;
  }
  p {
    margin: 0;
    font-size: 13px;
    opacity: 0.82;
  }
}
</style>

import { ref } from 'vue';
import { defineStore } from 'pinia';

import { getUnreadCount } from '@/api/notification';
import { ApiError } from '@/api/http';

export const useNotificationStore = defineStore('notification', () => {
  const unreadTotal = ref(0);
  const byType = ref<Record<string, number>>({});

  async function refresh(): Promise<void> {
    try {
      const data = await getUnreadCount();
      unreadTotal.value = data.total;
      byType.value = data.byType ?? {};
    } catch (err) {
      if (err instanceof ApiError && err.code === 40002) return;
      // 静默失败：未读数不是关键路径
      unreadTotal.value = 0;
    }
  }

  function reset(): void {
    unreadTotal.value = 0;
    byType.value = {};
  }

  return { unreadTotal, byType, refresh, reset };
});

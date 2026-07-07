import { createApp } from 'vue';
import { createPinia } from 'pinia';

import 'element-plus/dist/index.css';
import './styles/index.scss';
import './styles/element-overrides.scss';

import App from './App.vue';
import router from './router';
import { useAuthStore } from './stores/auth';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

// 启动后从 localStorage 恢复登录态，再挂载，避免守卫首次跳转闪烁
const auth = useAuthStore();
auth
  .restore()
  .catch(() => {
    /* 恢复失败由守卫接管 */
  })
  .finally(() => {
    app.mount('#app');
  });

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

const auth = useAuthStore();
auth
  .restore()
  .catch(() => {})
  .finally(() => {
    app.mount('#app');
  });

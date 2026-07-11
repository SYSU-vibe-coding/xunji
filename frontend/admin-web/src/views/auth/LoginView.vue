<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';

import { loginAdmin } from '@/api/auth';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const formRef = ref<FormInstance>();
const form = reactive({ account: '', password: '' });

const rules: FormRules = {
  account: [
    { required: true, message: '请输入账号' },
    { min: 3, max: 64, message: '账号长度 3-64 位' },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, max: 32, message: '密码长度 6-32 位' },
  ],
};

const submitting = ref(false);

async function submit() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid) return;
    const data = await loginAdmin(form.account.trim(), form.password);
    if (data.user.role !== 'ADMIN') {
      ElMessage.warning('该账号不具备后台权限');
      return;
    }
    auth.setSession(data);
    try {
      const profile = await auth.loadProfile();
      if (profile?.role !== 'ADMIN') {
        auth.clear();
        ElMessage.warning('该账号不具备后台权限');
        return;
      }
    } catch {
      auth.clear();
      throw new Error('账户信息加载失败，登录状态已回滚，请重试');
    }
    ElMessage.success('登录成功');
    const redirect = (route.query.redirect as string) || '/dashboard';
    void router.push(redirect);
  } catch (err) {
    ElMessage.error(err instanceof ApiError || err instanceof Error ? err.message : '登录失败');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <el-card class="auth-card" shadow="never">
    <header class="card-header">
      <span class="eyebrow">Admin sign in</span>
      <h2>后台登录</h2>
      <p>请使用管理员账号登录寻迹运营后台</p>
    </header>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @keyup.enter="submit"
    >
      <el-form-item label="账号" prop="account">
        <el-input v-model="form.account" placeholder="管理员账号" autocomplete="username" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          autocomplete="current-password"
          placeholder="至少 6 位"
        />
      </el-form-item>
      <el-button
        type="primary"
        size="large"
        class="submit"
        :loading="submitting"
        @click="submit"
      >
        登录
      </el-button>
    </el-form>
  </el-card>
</template>

<style scoped lang="scss">
.auth-card {
  width: 100%;
  max-width: 420px;
  border-radius: 16px;
  border: 1px solid var(--xunji-border);
}
.card-header {
  margin-bottom: 16px;

  .eyebrow {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  h2 {
    margin: 6px 0;
    font-size: 22px;
  }
  p {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}
.submit {
  width: 100%;
  margin-top: 8px;
}
</style>

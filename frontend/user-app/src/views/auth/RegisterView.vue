<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';

import { register, sendSmsCode } from '@/api/auth';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const auth = useAuthStore();

const form = reactive({ phone: '', code: '', nickname: '', password: '' });
const formRef = ref<FormInstance>();

const rules: FormRules = {
  phone: [
    { required: true, message: '请输入手机号' },
    { pattern: /^1\d{10}$/, message: '请输入 11 位大陆手机号', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入验证码' },
    { pattern: /^\d{6}$/, message: '验证码为 6 位数字' },
  ],
  nickname: [
    { required: true, message: '请输入昵称' },
    { min: 2, max: 20, message: '昵称 2-20 字' },
  ],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, max: 32, message: '密码 6-32 位' },
  ],
};

const sendingCode = ref(false);
const countdown = ref(0);
const submitting = ref(false);

async function sendCode() {
  if (!/^1\d{10}$/.test(form.phone)) {
    ElMessage.warning('请先输入正确的手机号');
    return;
  }
  sendingCode.value = true;
  try {
    const data = await sendSmsCode({ phone: form.phone });
    if (data.debugCode) form.code = data.debugCode;
    ElMessage.success('验证码已发送');
    countdown.value = data.expiresIn || 60;
    const timer = window.setInterval(() => {
      countdown.value -= 1;
      if (countdown.value <= 0) window.clearInterval(timer);
    }, 1000);
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '发送失败');
  } finally {
    sendingCode.value = false;
  }
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitting.value = true;
  try {
    const data = await register(form);
    auth.setSession(data);
    await auth.loadProfile();
    ElMessage.success('注册成功');
    void router.push('/');
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '注册失败');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <el-card class="auth-card" shadow="never">
    <header class="card-header">
      <span class="eyebrow">Sign up</span>
      <h2>加入寻迹</h2>
      <p>完成注册即可发布失物 / 招领，体验智能匹配</p>
    </header>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @keyup.enter="submit"
    >
      <el-form-item label="手机号" prop="phone">
        <el-input v-model="form.phone" maxlength="11" placeholder="13800000010" />
      </el-form-item>
      <el-form-item label="验证码" prop="code">
        <div class="code-row">
          <el-input v-model="form.code" maxlength="6" placeholder="6 位验证码" />
          <el-button :loading="sendingCode" :disabled="countdown > 0" @click="sendCode">
            {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
          </el-button>
        </div>
      </el-form-item>
      <el-form-item label="昵称" prop="nickname">
        <el-input v-model="form.nickname" maxlength="20" placeholder="同学昵称" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
      </el-form-item>
      <el-button
        type="primary"
        class="submit"
        size="large"
        :loading="submitting"
        @click="submit"
      >
        注册并登录
      </el-button>
    </el-form>

    <footer class="footer">
      已经有账号？<router-link to="/auth/login">直接登录</router-link>
    </footer>
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
.code-row {
  display: flex;
  gap: 8px;
  width: 100%;
  .el-input {
    flex: 1;
  }
}
.submit {
  width: 100%;
  margin-top: 8px;
}
.footer {
  margin-top: 16px;
  text-align: center;
  color: var(--xunji-text-muted);
  font-size: 13px;
  a {
    color: var(--el-color-primary);
    font-weight: 600;
  }
}
</style>

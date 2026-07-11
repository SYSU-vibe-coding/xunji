<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';

import { loginByPassword, loginBySmsCode, sendSmsCode } from '@/api/auth';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const notice = useNotificationStore();

const tab = ref<'password' | 'sms'>('password');

const passwordForm = reactive({ phone: '', password: '' });
const smsForm = reactive({ phone: '', code: '' });

const passwordFormRef = ref<FormInstance>();
const smsFormRef = ref<FormInstance>();

const phoneRule = { pattern: /^1\d{10}$/, message: '请输入 11 位大陆手机号', trigger: 'blur' };

const passwordRules: FormRules = {
  phone: [{ required: true, message: '请输入手机号' }, phoneRule],
  password: [
    { required: true, message: '请输入密码' },
    { min: 6, max: 32, message: '密码长度 6-32 位', trigger: 'blur' },
  ],
};

const smsRules: FormRules = {
  phone: [{ required: true, message: '请输入手机号' }, phoneRule],
  code: [
    { required: true, message: '请输入验证码' },
    { pattern: /^\d{6}$/, message: '验证码为 6 位数字', trigger: 'blur' },
  ],
};

const sendingCode = ref(false);
const submitting = ref(false);
const countdown = ref(0);

async function handleSendCode() {
  if (sendingCode.value || countdown.value > 0) return;
  if (!/^1\d{10}$/.test(smsForm.phone)) {
    ElMessage.warning('请先输入正确的手机号');
    return;
  }
  sendingCode.value = true;
  try {
    const data = await sendSmsCode({ phone: smsForm.phone });
    if (data.debugCode) {
      smsForm.code = data.debugCode;
      ElMessage.success('开发环境已自动填入验证码');
    } else {
      ElMessage.success('验证码已发送');
    }
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

async function afterLogin() {
  try {
    await auth.loadProfile();
  } catch {
    auth.clear();
    throw new Error('账户信息加载失败，登录状态已回滚，请重试');
  }
  await notice.refresh().catch(() => {});
  const redirect = (route.query.redirect as string) || '/';
  void router.push(redirect);
}

async function submitPassword() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    if (!passwordFormRef.value) {
      ElMessage.warning('页面尚未就绪，请稍后再试');
      return;
    }
    let valid = false;
    try {
      valid = await passwordFormRef.value.validate();
    } catch {
      valid = false;
    }
    if (!valid) {
      ElMessage.warning('请完整填写登录信息');
      return;
    }
    const data = await loginByPassword(passwordForm.phone, passwordForm.password);
    auth.setSession(data);
    await afterLogin();
    ElMessage.success('登录成功');
  } catch (err) {
    ElMessage.error(err instanceof ApiError || err instanceof Error ? err.message : '登录失败');
  } finally {
    submitting.value = false;
  }
}

async function submitSms() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    if (!smsFormRef.value) {
      ElMessage.warning('页面尚未就绪，请稍后再试');
      return;
    }
    let valid = false;
    try {
      valid = await smsFormRef.value.validate();
    } catch {
      valid = false;
    }
    if (!valid) {
      ElMessage.warning('请完整填写登录信息');
      return;
    }
    const data = await loginBySmsCode(smsForm.phone, smsForm.code);
    auth.setSession(data);
    await afterLogin();
    ElMessage.success('登录成功');
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
      <span class="eyebrow">Sign in</span>
      <h2>欢迎回到寻迹</h2>
      <p>使用校园手机号登录，开始管理你的失物与认领</p>
    </header>

    <el-tabs v-model="tab" class="tabs">
      <el-tab-pane label="密码登录" name="password">
        <el-form
          ref="passwordFormRef"
          :model="passwordForm"
          :rules="passwordRules"
          label-position="top"
          @keyup.enter="submitPassword"
        >
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="passwordForm.phone" maxlength="11" placeholder="13800000010" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="passwordForm.password"
              type="password"
              show-password
              placeholder="至少 6 位"
            />
          </el-form-item>
          <el-button
            type="primary"
            class="submit"
            size="large"
            native-type="button"
            :loading="submitting"
            @click="submitPassword"
          >
            登录
          </el-button>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="验证码登录" name="sms">
        <el-form
          ref="smsFormRef"
          :model="smsForm"
          :rules="smsRules"
          label-position="top"
          @keyup.enter="submitSms"
        >
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="smsForm.phone" maxlength="11" placeholder="13800000010" />
          </el-form-item>
          <el-form-item label="验证码" prop="code">
            <div class="code-row">
              <el-input v-model="smsForm.code" maxlength="6" placeholder="6 位验证码" />
              <el-button
                :loading="sendingCode"
                :disabled="countdown > 0"
                @click="handleSendCode"
              >
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>
          <el-button
            type="primary"
            class="submit"
            size="large"
            native-type="button"
            :loading="submitting"
            @click="submitSms"
          >
            登录
          </el-button>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <footer class="footer">
      还没有账号？<router-link to="/auth/register">立即注册</router-link>
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
.tabs :deep(.el-tabs__item) {
  font-size: 14px;
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

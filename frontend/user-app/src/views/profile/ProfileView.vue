<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Box, Edit, Medal, Promotion, SwitchButton, Trophy } from '@element-plus/icons-vue';

import StatusTag from '@/components/StatusTag.vue';
import ImageUploader from '@/components/ImageUploader.vue';
import { cancelMyAccount, updateMyProfile } from '@/api/user';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import { getInitial } from '@/utils/format';

const router = useRouter();
const auth = useAuthStore();

const editing = ref(false);
const editForm = reactive({ nickname: '', avatarRefs: [] as string[], previewUrls: [] as string[] });
const saving = ref(false);
const avatarUploading = ref(false);
const avatarUploadError = ref<string | null>(null);

function openEdit() {
  if (!auth.profile) return;
  editForm.nickname = auth.profile.nickname;
  editForm.avatarRefs = auth.profile.avatarRef ? [auth.profile.avatarRef] : [];
  editForm.previewUrls = auth.profile.avatarUrl ? [auth.profile.avatarUrl] : [];
  avatarUploading.value = false;
  avatarUploadError.value = null;
  editing.value = true;
}

async function saveEdit() {
  if (avatarUploading.value || avatarUploadError.value) {
    ElMessage.warning(avatarUploading.value ? '头像仍在上传，请稍候' : '头像上传失败，请重试');
    return;
  }
  if (!editForm.nickname.trim()) {
    ElMessage.warning('昵称不能为空');
    return;
  }
  saving.value = true;
  try {
    await updateMyProfile({
      nickname: editForm.nickname.trim(),
      avatarRef: editForm.avatarRefs[0],
    });
    await auth.loadProfile();
    ElMessage.success('资料已更新');
    editing.value = false;
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '保存失败');
  } finally {
    saving.value = false;
  }
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm(
      '注销后账号将无法登录，且关联的失物 / 招领将关闭，确定继续吗？',
      '注销账号',
      { type: 'warning', confirmButtonText: '确认注销', cancelButtonText: '我再想想' },
    );
  } catch {
    return;
  }
  try {
    await cancelMyAccount();
    ElMessage.success('账号已注销');
    auth.logout();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  }
}

onMounted(async () => {
  if (!auth.profile) {
    await auth.loadProfile().catch(() => {});
  }
});
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="hero xunji-hero">
      <div class="hero-row">
        <el-avatar :size="64" :src="auth.profile?.avatarUrl ?? undefined" class="avatar">
          {{ getInitial(auth.profile?.nickname) }}
        </el-avatar>
        <div class="info">
          <div class="row">
            <h1>{{ auth.profile?.nickname ?? '同学' }}</h1>
            <StatusTag variant="cert" :value="auth.profile?.certStatus ?? 'UNVERIFIED'" />
          </div>
          <p>{{ auth.profile?.phone ?? '—' }} · {{ auth.profile?.campusId ?? '未绑定校园编号' }}</p>
          <div class="actions">
            <el-button size="small" type="primary" plain @click="openEdit">
              <el-icon><Edit /></el-icon>编辑资料
            </el-button>
            <el-button size="small" plain @click="auth.logout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <section class="cards">
      <el-card shadow="never" class="link-card" @click="router.push('/profile/items')">
        <el-icon :size="22" color="#0d4f4f"><Box /></el-icon>
        <strong>我的发布</strong>
        <small>管理已发布的失物 / 招领</small>
      </el-card>
      <el-card shadow="never" class="link-card" @click="router.push('/profile/certification')">
        <el-icon :size="22" color="#7c3aed"><Medal /></el-icon>
        <strong>实名认证</strong>
        <small>提交证件 · 解锁认领特权</small>
      </el-card>
      <el-card shadow="never" class="link-card" @click="router.push('/profile/credits')">
        <el-icon :size="22" color="#f59e0b"><Trophy /></el-icon>
        <strong>信誉积分</strong>
        <small>查看积分变动流水</small>
      </el-card>
      <el-card shadow="never" class="link-card" @click="router.push('/claims')">
        <el-icon :size="22" color="#14b8a6"><Promotion /></el-icon>
        <strong>我的认领</strong>
        <small>跟进认领进度与凭证</small>
      </el-card>
    </section>

    <el-card shadow="never" class="danger-zone">
      <strong>账号注销</strong>
      <p>注销后账号将无法登录，所有活动失物与招领会关闭，关联匹配和待执行任务会失效</p>
      <el-button type="danger" plain @click="handleCancel">注销账号</el-button>
    </el-card>

    <el-dialog v-model="editing" title="编辑资料" width="420px">
      <el-form label-position="top">
        <el-form-item label="昵称">
          <el-input v-model="editForm.nickname" maxlength="20" />
        </el-form-item>
        <el-form-item label="头像（可选）">
          <ImageUploader
            v-model="editForm.avatarRefs"
            :preview-urls="editForm.previewUrls"
            biz-type="USER"
            :max="1"
            @uploading-change="avatarUploading = $event"
            @error-change="avatarUploadError = $event"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editing = false">取消</el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="avatarUploading || Boolean(avatarUploadError)"
          @click="saveEdit"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero {
  color: #fff;
  border: none;

  :deep(.el-card__body) {
    padding: 24px;
  }

  .hero-row {
    display: flex;
    gap: 18px;
    align-items: center;
    flex-wrap: wrap;

    .avatar {
      background: rgba(255, 255, 255, 0.18);
      color: #fff;
      font-weight: 700;
      font-size: 24px;
    }
    .info {
      flex: 1;
      min-width: 200px;

      .row {
        display: flex;
        align-items: center;
        gap: 10px;

        h1 {
          margin: 0;
          font-size: 22px;
          color: #fff;
        }
      }
      p {
        margin: 4px 0 12px;
        color: rgba(255, 255, 255, 0.78);
        font-size: 13px;
      }
      .actions {
        display: flex;
        gap: 8px;
      }
    }
  }
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.link-card {
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;

  :deep(.el-card__body) {
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  strong {
    font-weight: 600;
    color: var(--xunji-text);
  }
  small {
    color: var(--xunji-text-muted);
    font-size: 12px;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--xunji-shadow);
  }
}

.danger-zone {
  border-color: rgba(239, 68, 68, 0.4);

  :deep(.el-card__body) {
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }
  strong {
    color: var(--el-color-danger);
    font-size: 15px;
  }
  p {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}
</style>

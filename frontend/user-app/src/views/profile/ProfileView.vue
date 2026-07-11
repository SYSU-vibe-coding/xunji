<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  ArrowRight,
  Box,
  Edit,
  Medal,
  Promotion,
  SwitchButton,
  Trophy,
} from '@element-plus/icons-vue';

import StatusTag from '@/components/StatusTag.vue';
import ImageUploader from '@/components/ImageUploader.vue';
import { cancelMyAccount, updateMyProfile } from '@/api/user';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import { getInitial } from '@/utils/format';

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
    <el-card shadow="never" class="profile-panel">
      <div class="hero-row">
        <el-avatar :size="64" :src="auth.profile?.avatarUrl ?? undefined" class="avatar">
          {{ getInitial(auth.profile?.nickname) }}
        </el-avatar>
        <div class="info">
          <div class="row">
            <h1>{{ auth.profile?.nickname ?? '同学' }}</h1>
            <StatusTag variant="cert" :value="auth.profile?.certStatus ?? 'UNVERIFIED'" />
          </div>
          <div class="identity-meta">
            <span>{{ auth.profile?.phone ?? '—' }}</span>
            <span>{{ auth.profile?.campusId ?? '未绑定校园编号' }}</span>
          </div>
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

    <section class="account-section">
      <header class="section-header">
        <span>账号与业务</span>
        <small>管理身份、发布和认领记录</small>
      </header>
      <div class="cards">
        <RouterLink to="/profile/items" class="link-card">
          <span class="entry-icon primary"><el-icon :size="21"><Box /></el-icon></span>
          <span class="entry-copy">
            <strong>我的发布</strong>
            <small>管理已发布的失物 / 招领</small>
          </span>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </RouterLink>
        <RouterLink to="/profile/certification" class="link-card">
          <span class="entry-icon accent"><el-icon :size="21"><Medal /></el-icon></span>
          <span class="entry-copy">
            <strong>实名认证</strong>
            <small>提交证件，解锁认领特权</small>
          </span>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </RouterLink>
        <RouterLink to="/profile/credits" class="link-card">
          <span class="entry-icon warm"><el-icon :size="21"><Trophy /></el-icon></span>
          <span class="entry-copy">
            <strong>信誉积分</strong>
            <small>查看积分变动流水</small>
          </span>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </RouterLink>
        <RouterLink to="/claims" class="link-card">
          <span class="entry-icon success"><el-icon :size="21"><Promotion /></el-icon></span>
          <span class="entry-copy">
            <strong>我的认领</strong>
            <small>跟进认领进度与凭证</small>
          </span>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </RouterLink>
      </div>
    </section>

    <el-card shadow="never" class="danger-zone">
      <div class="danger-copy">
        <strong>账号注销</strong>
        <p>注销后无法恢复登录，活动中的失物、招领和待执行任务也会关闭。</p>
      </div>
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
  gap: 22px;
  min-width: 0;
}

.profile-panel {
  position: relative;
  overflow: hidden;
  border-color: #d7e7e5;
  background: #eef6f5;

  &::before {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 4px;
    background: var(--xunji-primary);
    content: '';
  }

  :deep(.el-card__body) {
    padding: 26px 28px;
  }

  .hero-row {
    display: flex;
    gap: 20px;
    align-items: center;

    .avatar {
      flex: 0 0 auto;
      border: 3px solid rgba(255, 255, 255, 0.88);
      background: var(--xunji-primary);
      color: #fff;
      font-weight: 700;
      font-size: 24px;
      box-shadow: 0 2px 10px rgba(13, 79, 79, 0.12);
    }

    .info {
      flex: 1;
      min-width: 0;

      .row {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;

        h1 {
          margin: 0;
          color: var(--xunji-text);
          font-size: 23px;
          letter-spacing: -0.02em;
        }
      }

      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 15px;

        .el-button {
          min-height: 38px;
          margin-left: 0;
        }
      }
    }
  }
}

.identity-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 16px;
  margin-top: 7px;
  color: var(--xunji-text-muted);
  font-size: 13px;

  span + span {
    position: relative;

    &::before {
      position: absolute;
      top: 50%;
      left: -9px;
      width: 3px;
      height: 3px;
      border-radius: 50%;
      background: #94a3b8;
      content: '';
      transform: translateY(-50%);
    }
  }
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;

  span {
    color: var(--xunji-text);
    font-size: 17px;
    font-weight: 700;
  }

  small {
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}

.cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.link-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  min-height: 104px;
  gap: 14px;
  padding: 20px;
  border: 1px solid var(--xunji-border);
  border-radius: var(--xunji-radius);
  background: var(--xunji-surface);
  box-shadow: var(--xunji-shadow-sm);
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;

  .entry-icon {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    border-radius: 12px;

    &.primary {
      background: #e7f1f0;
      color: var(--xunji-primary);
    }

    &.accent {
      background: var(--xunji-accent-soft);
      color: var(--xunji-accent);
    }

    &.warm {
      background: #fef3df;
      color: #b97608;
    }

    &.success {
      background: #e7f9f6;
      color: #0d8b7d;
    }
  }

  .entry-copy {
    min-width: 0;
  }

  strong,
  small {
    display: block;
  }

  strong {
    font-weight: 600;
    color: var(--xunji-text);
  }

  small {
    margin-top: 4px;
    color: var(--xunji-text-muted);
    font-size: 12px;
    line-height: 1.4;
  }

  .entry-arrow {
    color: #94a3b8;
  }

  &:focus-visible {
    outline: 3px solid rgba(13, 79, 79, 0.18);
    outline-offset: 2px;
  }

  @media (hover: hover) {
    &:hover {
      border-color: #b6d6d6;
      box-shadow: var(--xunji-shadow);
      transform: translateY(-2px);
    }
  }
}

.danger-zone {
  border-color: var(--xunji-border);
  border-left: 3px solid rgba(239, 68, 68, 0.55);

  :deep(.el-card__body) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 18px 20px;
  }

  .danger-copy {
    min-width: 0;
  }

  strong {
    color: var(--xunji-text);
    font-size: 15px;
  }

  p {
    margin: 5px 0 0;
    color: var(--xunji-text-muted);
    font-size: 13px;
    line-height: 1.5;
  }

  .el-button {
    flex: 0 0 auto;
    min-height: 40px;
    margin-left: 0;
  }
}

@media (max-width: 720px) {
  .page {
    gap: 18px;
  }

  .profile-panel {
    :deep(.el-card__body) {
      padding: 20px 18px 20px 20px;
    }

    .hero-row {
      align-items: flex-start;
      gap: 14px;

      .avatar {
        width: 54px;
        height: 54px;
        font-size: 20px;
      }

      .info .row h1 {
        font-size: 20px;
      }

      .info .actions {
        gap: 8px;
        margin-top: 13px;

        .el-button {
          min-height: 44px;
        }
      }
    }
  }

  .identity-meta {
    gap: 3px;
    margin-top: 5px;

    span {
      display: block;
      width: 100%;
    }

    span + span::before {
      display: none;
    }
  }

  .account-section {
    overflow: hidden;
    border: 1px solid var(--xunji-border);
    border-radius: var(--xunji-radius);
    background: var(--xunji-surface);
  }

  .section-header {
    display: block;
    margin: 0;
    padding: 16px 16px 12px;
    border-bottom: 1px solid var(--xunji-border);

    span,
    small {
      display: block;
    }

    small {
      margin-top: 3px;
    }
  }

  .cards {
    display: block;
  }

  .link-card {
    min-height: 72px;
    padding: 12px 14px;
    border: 0;
    border-bottom: 1px solid var(--xunji-border);
    border-radius: 0;
    box-shadow: none;

    &:last-child {
      border-bottom: 0;
    }

    .entry-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
    }
  }

  .danger-zone :deep(.el-card__body) {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;

    .el-button {
      min-height: 44px;
    }
  }
}
</style>

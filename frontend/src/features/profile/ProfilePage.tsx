import { useState } from 'react';
import { Bookmark, History, LockKeyhole, UserRound, ArrowRight, Check } from 'lucide-react';
import { api, setCsrf } from '../../shared/api/api';
import type { Disease, User } from '../../shared/types/index';
import { Heading } from '../../shared/components/Heading';
import { TopicCard } from '../library/components/TopicCard';

export function ProfilePage({
  user,
  updateUser,
  saved,
  savedError,
  retrySaved,
  open,
  unsave,
  history,
  auth,
}: {
  user: User | null;
  updateUser: (u: User) => void;
  saved: Disease[];
  savedError: string;
  retrySaved: () => void;
  open: (d: Disease) => void;
  unsave: (id: string) => Promise<void>;
  history: () => void;
  auth: () => void;
}) {
  const [name, setName] = useState(user?.name || '');
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [repeat, setRepeat] = useState('');
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState({ area: '', text: '', error: false });
  const notify = (area: string, text: string, error = false) => setMessage({ area, text, error });
  const feedback = (area: string) =>
    message.area === area && (
      <p
        className={message.error ? 'error-text' : 'profile-success'}
        role={message.error ? 'alert' : 'status'}
      >
        {!message.error && <Check size={16} />}
        {message.text}
      </p>
    );
  if (!user)
    return (
      <div className="empty">
        <UserRound size={36} />
        <h2>Không gian cá nhân của bạn</h2>
        <p>Đăng nhập để quản lý tài khoản và các bài viết đã lưu.</p>
        <button className="button primary" onClick={auth}>
          Đăng nhập <ArrowRight size={17} />
        </button>
      </div>
    );
  const submitName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    if (!name.trim()) {
      notify('info', 'Vui lòng nhập tên của bạn.', true);
      return;
    }
    setBusy('info');
    try {
      const r = await api<{ user: User }>('/auth/profile', {
        method: 'PATCH',
        body: JSON.stringify({ name: name.trim() }),
      });
      updateUser(r.user);
      setName(r.user.name);
      notify('info', 'Đã cập nhật thông tin.');
    } catch (e) {
      notify('info', (e as Error).message, true);
    } finally {
      setBusy('');
    }
  };
  const submitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    if (password !== repeat) {
      notify('password', 'Mật khẩu xác nhận chưa khớp.', true);
      return;
    }
    setBusy('password');
    try {
      const r = await api<{ user: User; csrf: string }>('/auth/password', {
        method: 'POST',
        body: JSON.stringify({ current_password: current, new_password: password }),
      });
      setCsrf(r.csrf);
      updateUser(r.user);
      setCurrent('');
      setPassword('');
      setRepeat('');
      notify('password', 'Đã đổi mật khẩu. Các thiết bị khác đã được đăng xuất.');
    } catch (e) {
      notify('password', (e as Error).message, true);
    } finally {
      setBusy('');
    }
  };
  return (
    <>
      <Heading
        eyebrow="KHÔNG GIAN CÁ NHÂN"
        title="Góc nhỏ dành riêng cho bạn."
        description="Quản lý tài khoản và giữ lại những thông tin bạn quan tâm."
      />
      <section className="profile-banner">
        <span className="profile-avatar" aria-hidden="true">
          {user.name.charAt(0).toUpperCase()}
        </span>
        <div>
          <span className="eyebrow">
            {user.role === 'admin' ? 'QUẢN TRỊ VIÊN' : 'THÀNH VIÊN DERMA'}
          </span>
          <h2>{user.name}</h2>
          <p>{user.email}</p>
        </div>
        <button className="button secondary" onClick={history}>
          <History size={18} />
          Lịch sử tra cứu <ArrowRight size={17} />
        </button>
      </section>
      <div className="profile-settings">
        <section className="profile-panel">
          <h2>
            <UserRound size={21} />
            Thông tin cá nhân
          </h2>
          <p className="muted">Tên hiển thị giúp bạn dễ nhận biết tài khoản của mình.</p>
          <form className="auth-form" onSubmit={submitName}>
            <label>
              Họ tên
              <input
                autoComplete="name"
                required
                maxLength={80}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              Email đăng nhập
              <input
                type="email"
                value={user.email}
                readOnly
                aria-describedby="profile-email-note"
              />
            </label>
            <small id="profile-email-note" className="muted">
              Email được giữ cố định để bảo vệ thông tin đăng nhập.
            </small>
            {feedback('info')}
            <button className="button primary" disabled={!!busy}>
              {busy === 'info' ? 'Đang lưu…' : 'Lưu thay đổi'}
            </button>
          </form>
        </section>
        <section className="profile-panel">
          <h2>
            <LockKeyhole size={21} />
            Bảo mật tài khoản
          </h2>
          <p className="muted">Dùng mật khẩu riêng cho tài khoản Derma.</p>
          <form className="auth-form" onSubmit={submitPassword}>
            <label>
              Mật khẩu hiện tại
              <input
                type="password"
                autoComplete="current-password"
                required
                maxLength={128}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </label>
            <label>
              Mật khẩu mới
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={6}
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <small>Từ 6–128 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.</small>
            </label>
            <label>
              Xác nhận mật khẩu mới
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={6}
                maxLength={128}
                value={repeat}
                onChange={(e) => setRepeat(e.target.value)}
              />
            </label>
            {feedback('password')}
            <button className="button secondary" disabled={!!busy}>
              {busy === 'password' ? 'Đang cập nhật…' : 'Đổi mật khẩu'}
            </button>
          </form>
        </section>
      </div>
      <section className="profile-bookmarks">
        <div className="profile-section-heading">
          <div>
            <span className="eyebrow">ĐỌC TIẾP BẤT CỨ LÚC NÀO</span>
            <h2>
              <Bookmark size={23} />
              Bài viết đã lưu <span className="category-badge">{saved.length}</span>
            </h2>
          </div>
        </div>
        {savedError ? (
          <div className="inline-note error" role="alert">
            {savedError}
            <button className="button secondary" onClick={retrySaved}>
              Thử lại
            </button>
          </div>
        ) : saved.length ? (
          <div className="profile-saved-grid">
            {saved.map((d, i) => (
              <div key={d.id} className="profile-saved-item">
                <TopicCard disease={d} index={i} open={() => open(d)} />
                <button
                  className="button secondary"
                  disabled={!!busy}
                  onClick={async () => {
                    setBusy(d.id);
                    try {
                      await unsave(d.id);
                    } catch (e) {
                      notify('saved', (e as Error).message, true);
                    } finally {
                      setBusy('');
                    }
                  }}
                >
                  Bỏ lưu bài viết
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty">
            <Bookmark size={32} />
            <h3>Chưa có bài viết đã lưu</h3>
            <p>Mở một bài trong thư viện và chọn “Lưu bài viết” để thêm vào đây.</p>
          </div>
        )}
        {feedback('saved')}
      </section>
    </>
  );
}

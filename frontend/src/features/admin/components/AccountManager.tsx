import { useEffect, useState } from 'react';
import { api } from '../../../shared/api/api';
import type { User } from '../../../shared/types/index';

export function AccountManager({
  currentUser,
  toast,
}: {
  currentUser: User;
  toast: (text: string) => void;
}) {
  const [users, setUsers] = useState<User[]>([]);
  const [q, setQ] = useState('');
  const [role, setRole] = useState('');
  const [editing, setEditing] = useState<User | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function load() {
    try {
      setUsers(await api<User[]>('/admin/users'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const visible = users.filter(
    (u) =>
      (!role || u.role === role) && `${u.name} ${u.email}`.toLowerCase().includes(q.toLowerCase()),
  );
  return (
    <section className="panel account-manager">
      <div className="section-title">
        <h2>Quản lý tài khoản</h2>
        <span className="state-badge">{users.length} tài khoản</span>
      </div>
      <div className="management-toolbar">
        <input
          aria-label="Tìm tài khoản"
          placeholder="Tìm theo tên hoặc email…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          aria-label="Lọc quyền tài khoản"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          <option value="">Tất cả quyền</option>
          <option value="user">Người dùng</option>
          <option value="admin">Quản trị viên</option>
        </select>
      </div>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tài khoản</th>
              <th>Email</th>
              <th>Quyền</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((u) => (
              <tr key={u.id}>
                <td>
                  {u.name}
                  {u.id === currentUser.id && ' (bạn)'}
                </td>
                <td>{u.email}</td>
                <td>{u.role === 'admin' ? 'Quản trị viên' : 'Người dùng'}</td>
                <td>
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => setEditing({ ...u })}
                  >
                    Chỉnh sửa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!visible.length && <p className="muted">Không có tài khoản phù hợp.</p>}
      {editing && (
        <form
          className="account-editor auth-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const previousRole = users.find((u) => u.id === editing.id)?.role;
            if (
              previousRole !== editing.role &&
              !window.confirm(
                `Đổi quyền của ${editing.email} sang ${editing.role === 'admin' ? 'quản trị viên' : 'người dùng'}? Các phiên đăng nhập của tài khoản này sẽ kết thúc.`,
              )
            )
              return;
            setBusy(true);
            setError('');
            try {
              await api('/admin/users/' + editing.id, {
                method: 'PUT',
                body: JSON.stringify({ name: editing.name, role: editing.role }),
              });
              setEditing(null);
              await load();
              toast('Đã cập nhật tài khoản. Thay đổi quyền yêu cầu tài khoản đó đăng nhập lại.');
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <h3>Chỉnh sửa {editing.email}</h3>
          <label>
            Tên hiển thị
            <input
              required
              maxLength={80}
              value={editing.name}
              onChange={(e) => setEditing({ ...editing, name: e.target.value })}
            />
          </label>
          <label>
            Quyền truy cập
            <select
              disabled={editing.id === currentUser.id}
              value={editing.role}
              onChange={(e) => setEditing({ ...editing, role: e.target.value })}
            >
              <option value="user">Người dùng</option>
              <option value="admin">Quản trị viên</option>
            </select>
          </label>
          <p className="muted">
            Không thể tự gỡ quyền admin. Đổi quyền sẽ kết thúc các phiên đăng nhập của tài khoản
            được sửa.
          </p>
          <div className="modal-actions">
            <button
              className="button secondary"
              type="button"
              disabled={busy}
              onClick={() => setEditing(null)}
            >
              Hủy
            </button>
            <button className="button primary" disabled={busy}>
              {busy ? 'Đang lưu…' : 'Lưu tài khoản'}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

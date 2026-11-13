import React, { useEffect, useId, useRef, useState } from 'react';
import { ArrowRight, Eye, EyeOff, LockKeyhole, Sparkles } from 'lucide-react';
import { api, setCsrf } from '../../../shared/api/api';
import type { User } from '../../../shared/types/index';
import { Modal } from '../../../shared/components/Modal';

export function AuthModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (u: User) => void;
}) {
  const id = useId();
  const errorRef = useRef<HTMLDivElement>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [register, setRegister] = useState(false),
    [email, setEmail] = useState(''),
    [password, setPassword] = useState(''),
    [name, setName] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      register &&
      !(
        password.length >= 6 &&
        password.length <= 128 &&
        /[A-Z]/.test(password) &&
        /[a-z]/.test(password) &&
        /[0-9]/.test(password) &&
        /[!"#$%&'()*+,\-./:;<=>?@[\]\\^_`{|}~]/.test(password)
      )
    ) {
      setError('Mật khẩu phải có từ 6–128 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const r = await api<{ user: User; csrf: string }>(
        '/auth/' + (register ? 'register' : 'login'),
        { method: 'POST', body: JSON.stringify({ email, password, name: name || 'Bạn đọc' }) },
      );
      setCsrf(r.csrf);
      onSuccess(r.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title={register ? 'Tạo tài khoản' : 'Chào mừng bạn trở lại'} onClose={onClose}>
      <div className="auth-emblem" aria-hidden="true">
        <LockKeyhole size={30} />
        <span>
          <Sparkles size={16} />
        </span>
      </div>
      <p className="muted">
        Đăng nhập để lưu những điều bạn muốn tìm hiểu. Lịch sử luôn do bạn lựa chọn.
      </p>
      <form onSubmit={submit} className="auth-form">
        {error && (
          <div
            className="form-error-summary"
            role="alert"
            tabIndex={-1}
            ref={errorRef}
            id={id + '-error'}
          >
            <strong>{register ? 'Chưa thể tạo tài khoản' : 'Chưa thể đăng nhập'}</strong>
            <p>{error}</p>
          </div>
        )}
        {register && (
          <label>
            Tên của bạn
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={80}
              autoComplete="name"
            />
          </label>
        )}
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            maxLength={254}
            autoComplete="email"
            placeholder="ban@example.com"
          />
        </label>
        <label>
          Mật khẩu
          <span className="password-control">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              maxLength={128}
              autoComplete={register ? 'new-password' : 'current-password'}
              aria-describedby={register ? id + '-password-hint' : undefined}
            />
            <button
              type="button"
              aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
              aria-pressed={showPassword}
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff size={18} aria-hidden="true" />
              ) : (
                <Eye size={18} aria-hidden="true" />
              )}
            </button>
          </span>
          {register && (
            <small id={id + '-password-hint'}>
              Từ 6–128 ký tự, có chữ hoa, chữ thường, số và ký tự đặc biệt.
            </small>
          )}
        </label>
        <button className="button primary full" disabled={busy} aria-busy={busy}>
          {busy ? 'Đang xử lý…' : register ? 'Tạo tài khoản' : 'Đăng nhập'}
          <ArrowRight size={17} />
        </button>
      </form>
      <button
        className="auth-switch"
        onClick={() => {
          setRegister(!register);
          setError('');
          setShowPassword(false);
        }}
      >
        {register ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký'}
      </button>
    </Modal>
  );
}

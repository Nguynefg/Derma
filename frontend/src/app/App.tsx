import type { ChatTurn, ImageChatContext } from '../features/assistant/components/AssistantChat';
import { SkinIllustration } from '../features/library/components/SkinIllustration';
import { lazy, Suspense, useEffect, useState } from 'react';
import {
  BookOpen,
  Bookmark,
  ChevronRight,
  CircleHelp,
  ExternalLink,
  History,
  Info,
  Layers3,
  LogOut,
  Menu,
  RefreshCw,
  ScanLine,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Stethoscope,
  UserRound,
  X,
} from 'lucide-react';
import { api, setCsrf } from '../shared/api/api';
import type { Disease, Symptom, User, Page, SearchResult } from '../shared/types/index';
import { Modal } from '../shared/components/Modal';
import { ThemeToggle, LoadingSkeleton } from '../shared/components/Visuals';
import { ReadingGuide, BackToTop } from '../shared/components/Decor';
import { HomePage } from '../pages/HomePage';
const ImagePage = lazy(() =>
  import('../features/images/ImagePage').then((module) => ({ default: module.ImagePage })),
);
const QuestionPage = lazy(() =>
  import('../features/assistant/QuestionPage').then((module) => ({ default: module.QuestionPage })),
);
import { AuthModal } from '../features/auth/components/AuthModal';
const LibraryPage = lazy(() =>
  import('../features/library/LibraryPage').then((module) => ({ default: module.LibraryPage })),
);
const SymptomPage = lazy(() =>
  import('../features/symptoms/SymptomPage').then((module) => ({ default: module.SymptomPage })),
);
const HistoryPage = lazy(() =>
  import('../features/history/HistoryPage').then((module) => ({ default: module.HistoryPage })),
);
const SourcesPage = lazy(() =>
  import('../pages/SourcesPage').then((module) => ({ default: module.SourcesPage })),
);
const AdminPage = lazy(() =>
  import('../features/admin/AdminPage').then((module) => ({ default: module.AdminPage })),
);
const ProfilePage = lazy(() =>
  import('../features/profile/ProfilePage').then((module) => ({ default: module.ProfilePage })),
);

const pageNames: Record<Page, string> = {
  home: 'Tổng quan',
  library: 'Thư viện bệnh lý',
  questions: 'Trợ lý AI',
  symptoms: 'Tra cứu triệu chứng',
  images: 'Kiểm tra hình ảnh',
  history: 'Lịch sử tra cứu',
  sources: 'Nguồn tham khảo',
  admin: 'Quản trị nội dung',
  profile: 'Tài khoản cá nhân',
};
const navItems = [
  { id: 'home', label: 'Tổng quan', icon: Layers3 },
  { id: 'library', label: 'Thư viện bệnh lý', icon: BookOpen },
  { id: 'questions', label: 'Trợ lý AI', icon: Sparkles },
  { id: 'symptoms', label: 'Tra cứu triệu chứng', icon: Stethoscope },
  { id: 'images', label: 'Kiểm tra hình ảnh', icon: ScanLine },
  { id: 'history', label: 'Lịch sử tra cứu', icon: History },
] as const;

export function App() {
  const [page, setPage] = useState<Page>('home');
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [imageContext, setImageContext] = useState<ImageChatContext | null>(null);
  const [mobile, setMobile] = useState(false);
  const [all, setAll] = useState<Disease[]>([]);
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [user, setUser] = useState<User | null>(null);
  const [saved, setSaved] = useState<Disease[]>([]);
  const [savedError, setSavedError] = useState('');
  const [savedReload, setSavedReload] = useState(0);
  const [bookmarkBusy, setBookmarkBusy] = useState(false);
  useEffect(() => {
    setSaved([]);
    setSavedError('');
    if (!user) return;
    const controller = new AbortController();
    api<Disease[]>('/bookmarks', { signal: controller.signal })
      .then((rows) => {
        if (!controller.signal.aborted) setSaved(rows);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setSavedError((e as Error).message);
      });
    return () => controller.abort();
  }, [user?.id, savedReload]);
  const unsave = async (id: string) => {
    await api('/bookmarks/' + id, { method: 'DELETE' });
    setSaved((rows) => rows.filter((d) => d.id !== id));
  };
  const toggleBookmark = async (d: Disease) => {
    if (!user) {
      setAuthOpen(true);
      return;
    }
    if (bookmarkBusy) return;
    setBookmarkBusy(true);
    try {
      if (saved.some((s) => s.id === d.id)) {
        await unsave(d.id);
        setToast('Đã bỏ lưu bài viết.');
      } else {
        await api('/bookmarks/' + d.id, { method: 'PUT' });
        setSaved((rows) => [d, ...rows.filter((s) => s.id !== d.id)]);
        setToast('Đã thêm vào bài viết đã lưu.');
      }
    } catch (e) {
      setToast((e as Error).message);
    } finally {
      setBookmarkBusy(false);
    }
  };
  const isAdmin = user?.role === 'admin';
  const needsLibrary = ['library', 'symptoms', 'sources', 'admin'].includes(page);
  useEffect(() => {
    if (!isAdmin && page === 'admin') setPage('home');
  }, [isAdmin, page]);
  const [authOpen, setAuthOpen] = useState(false);
  const [selected, setSelected] = useState<Disease | null>(null);
  const [toast, setToast] = useState('');
  const [initialQuery, setInitialQuery] = useState('');
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(''), 5000);
    return () => clearTimeout(t);
  }, [toast]);
  const load = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [d, s] = await Promise.all([
        api<SearchResult>('/diseases'),
        api<Symptom[]>('/symptoms'),
      ]);
      setAll(d.items);
      setSymptoms(s);
    } catch (e) {
      setLoadError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
    api<{ user: User; csrf: string }>('/auth/me')
      .then((r) => {
        setUser(r.user);
        setCsrf(r.csrf);
      })
      .catch(() => {});
  }, []);
  const go = (p: Page) => {
    if (p === 'admin' && !isAdmin) return;
    setPage(p);
    setMobile(false);
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'instant'
        : 'smooth',
    });
  };
  const search = (value: string) => {
    setInitialQuery(value);
    go('library');
  };
  const logout = async () => {
    try {
      await api('/auth/logout', { method: 'POST' });
      setUser(null);
      setChatTurns([]);
      setImageContext(null);
      setCsrf('');
      setToast('Bạn đã đăng xuất.');
      go('home');
    } catch (e) {
      setToast((e as Error).message);
    }
  };
  const showDisease = async (id: string) => {
    try {
      setSelected(await api<Disease>('/diseases/' + id));
    } catch (e) {
      setToast((e as Error).message);
    }
  };

  const shortNames: Record<Page, string> = {
    home: 'Trang chủ',
    library: 'Thư viện',
    questions: 'Trợ lý AI',
    symptoms: 'Triệu chứng',
    images: 'Hình ảnh',
    history: 'Lịch sử',
    sources: 'Nguồn',
    admin: 'Quản trị',
    profile: 'Tài khoản',
  };
  useEffect(() => {
    if (!mobile) return;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobile(false);
    };
    document.addEventListener('keydown', close);
    return () => {
      document.body.style.overflow = oldOverflow;
      document.removeEventListener('keydown', close);
    };
  }, [mobile]);
  return (
    <div className="app-shell">
      <a className="visually-hidden skip-link" href="#main-content">
        Đi đến nội dung chính
      </a>
      <header className="site-header">
        <div className="header-inner">
          <button className="brand" onClick={() => go('home')} aria-label="Derma trang chủ">
            <span className="brand-icon">
              <svg
                width="31"
                height="31"
                viewBox="7 8 34 32"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M24 15c-3.8-3-8.3-3.8-13-2.3v21c4.7-1.5 9.2-.7 13 2.3 3.8-3 8.3-3.8 13-2.3v-21c-4.7-1.5-9.2-.7-13 2.3Z" />
                <path d="M24 15v21M16 21l3 .7M16 26l3 .7M30.5 20v7M27 23.5h7" />
              </svg>
            </span>
            <span className="brand-word">
              <strong>
                derma<span className="brand-dot">.</span>
              </strong>
              <small>Thư viện sức khỏe đa chuyên khoa</small>
            </span>
          </button>
          <nav className="desktop-nav" aria-label="Điều hướng chính">
            {navItems.map((n) => (
              <button
                key={n.id}
                onClick={() => {
                  if (n.id === 'library') setInitialQuery('');
                  go(n.id);
                }}
                className={page === n.id ? 'active' : ''}
                aria-current={page === n.id ? 'page' : undefined}
                aria-label={n.label}
              >
                {shortNames[n.id]}
              </button>
            ))}
            <button
              className={page === 'sources' ? 'active' : ''}
              onClick={() => go('sources')}
              aria-label="Nguồn tham khảo"
            >
              Nguồn
            </button>
          </nav>
          <div className="header-actions">
            <ThemeToggle />
            {isAdmin && (
              <button
                className="icon-button admin-shortcut"
                aria-label="Quản trị"
                title="Quản trị"
                onClick={() => go('admin')}
              >
                <SlidersHorizontal size={19} />
              </button>
            )}
            {user ? (
              <>
                <button
                  className="profile-button"
                  onClick={() => go('profile')}
                  aria-label="Tài khoản cá nhân"
                >
                  <span>{user.name[0].toUpperCase()}</span>
                  {user.name}
                </button>
                <button className="icon-button" aria-label="Đăng xuất" onClick={logout}>
                  <LogOut size={18} />
                </button>
              </>
            ) : (
              <button
                className="login-button"
                onClick={() => {
                  setMobile(false);
                  setAuthOpen(true);
                }}
              >
                <UserRound size={17} />
                Đăng nhập
              </button>
            )}
            <button
              className="icon-button mobile-menu"
              onClick={() => setMobile((v) => !v)}
              aria-label="Mở menu"
              aria-expanded={mobile}
              aria-controls="mobile-navigation"
            >
              <Menu size={24} />
            </button>
          </div>
        </div>
      </header>
      {mobile && (
        <>
          <div className="sidebar-scrim" onClick={() => setMobile(false)} />
          <aside className="mobile-drawer" id="mobile-navigation">
            <div className="drawer-heading">
              <span>Menu Derma</span>
              <button
                className="icon-button"
                aria-label="Đóng menu"
                onClick={() => setMobile(false)}
              >
                <X size={23} />
              </button>
            </div>
            <nav className="drawer-nav" aria-label="Điều hướng di động">
              {navItems.map((n) => (
                <button
                  key={n.id}
                  onClick={() => {
                    if (n.id === 'library') setInitialQuery('');
                    go(n.id);
                  }}
                  className={page === n.id ? 'active' : ''}
                >
                  <n.icon size={21} />
                  {n.label}
                </button>
              ))}
              <button onClick={() => go('sources')}>
                <ShieldCheck size={21} />
                Nguồn tham khảo
              </button>
              {user && (
                <button onClick={() => go('profile')}>
                  <UserRound size={21} />
                  Tài khoản cá nhân
                </button>
              )}
              {isAdmin && (
                <button onClick={() => go('admin')}>
                  <SlidersHorizontal size={21} />
                  Quản trị
                </button>
              )}
            </nav>
            <p className="drawer-note">
              Thông tin hỗ trợ tìm hiểu.
              <br />
              Không thay thế bác sĩ.
            </p>
          </aside>
        </>
      )}
      {page !== 'home' && (
        <div className="subnav">
          <button onClick={() => go('home')}>Trang chủ</button>
          <ChevronRight size={14} />
          <strong>{pageNames[page]}</strong>
        </div>
      )}
      <main id="main-content" className={page === 'home' ? 'home-main' : ''}>
        <div className={'page-content page-' + page} key={page}>
          {loadError && needsLibrary ? (
            <div className="empty">
              <CircleHelp size={35} />
              <h2>Chưa tải được thư viện</h2>
              <p>{loadError}</p>
              <button className="button primary" onClick={load}>
                <RefreshCw size={16} />
                Thử lại
              </button>
            </div>
          ) : loading && needsLibrary ? (
            <LoadingSkeleton />
          ) : (
            <Suspense fallback={<LoadingSkeleton />}>
              {page === 'home' && (
                <HomePage
                  diseases={all}
                  search={search}
                  navigate={go}
                  open={setSelected}
                  loading={loading}
                  loadError={loadError}
                  retry={load}
                />
              )}
              {page === 'library' && (
                <LibraryPage
                  key={initialQuery}
                  initialQuery={initialQuery}
                  all={all}
                  open={setSelected}
                  user={user}
                  auth={() => setAuthOpen(true)}
                  toast={setToast}
                />
              )}
              {page === 'symptoms' && (
                <SymptomPage
                  symptoms={symptoms}
                  open={setSelected}
                  user={user}
                  auth={() => setAuthOpen(true)}
                  toast={setToast}
                />
              )}
              {page === 'questions' && (
                <QuestionPage
                  open={showDisease}
                  turns={chatTurns}
                  setTurns={setChatTurns}
                  context={imageContext}
                  clearContext={() => setImageContext(null)}
                />
              )}
              {page === 'images' && (
                <ImagePage
                  discuss={(context) => {
                    setImageContext(context);
                    go('questions');
                  }}
                  symptoms={() => go('symptoms')}
                  open={showDisease}
                  user={user}
                  auth={() => setAuthOpen(true)}
                />
              )}
              {page === 'history' && (
                <HistoryPage
                  user={user}
                  auth={() => setAuthOpen(true)}
                  open={showDisease}
                  toast={setToast}
                />
              )}
              {page === 'sources' && <SourcesPage all={all} />}
              {page === 'profile' && (
                <ProfilePage
                  key={user?.id || 'guest'}
                  user={user}
                  updateUser={setUser}
                  saved={saved}
                  savedError={savedError}
                  retrySaved={() => setSavedReload((n) => n + 1)}
                  open={setSelected}
                  unsave={unsave}
                  history={() => go('history')}
                  auth={() => setAuthOpen(true)}
                />
              )}
              {page === 'admin' && isAdmin && (
                <AdminPage
                  user={user}
                  auth={() => setAuthOpen(true)}
                  symptoms={symptoms}
                  refresh={load}
                  toast={setToast}
                />
              )}
            </Suspense>
          )}
        </div>
      </main>
      <BackToTop />
      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-intro">
            <button className="footer-brand" onClick={() => go('home')}>
              derma<span>.</span>
            </button>
            <p>
              Thư viện sức khỏe có nguồn tham khảo, giúp bạn tìm hiểu bệnh lý theo chuyên khoa và
              dấu hiệu.
            </p>
          </div>
          <div className="footer-links">
            <h3>Khám phá</h3>
            <button onClick={() => search('')}>Thư viện bệnh lý</button>
            <button onClick={() => go('symptoms')}>Tra cứu triệu chứng</button>
            <button onClick={() => go('questions')}>Trợ lý AI</button>
            <button onClick={() => go('images')}>Kiểm tra hình ảnh</button>
          </div>
          <div className="footer-links">
            <h3>Thông tin & tài khoản</h3>
            <button onClick={() => go('sources')}>Nguồn tham khảo</button>
            <button onClick={() => go('history')}>Lịch sử tra cứu</button>
            {user && <button onClick={() => go('profile')}>Tài khoản cá nhân</button>}
            {isAdmin && <button onClick={() => go('admin')}>Quản trị nội dung</button>}
          </div>
        </div>
        <div className="footer-bottom">
          <span>Derma · Bản nghiên cứu v0.2</span>
          <span>Thông tin hỗ trợ tra cứu, không thay thế bác sĩ.</span>
        </div>
      </footer>
      {selected && (
        <Modal title="Thông tin bệnh lý" onClose={() => setSelected(null)} wide>
          <div className="detail-kicker">
            {selected.specialty} <span>•</span> {selected.category} <span>•</span>{' '}
            {selected.english_name}
          </div>
          <h1 className="detail-title">{selected.name}</h1>
          <button
            className="button secondary detail-bookmark"
            disabled={bookmarkBusy}
            onClick={() => toggleBookmark(selected)}
            aria-pressed={saved.some((d) => d.id === selected.id)}
          >
            <Bookmark
              size={18}
              fill={saved.some((d) => d.id === selected.id) ? 'currentColor' : 'none'}
            />
            {bookmarkBusy
              ? 'Đang lưu…'
              : saved.some((d) => d.id === selected.id)
                ? 'Đã lưu · Bỏ lưu'
                : 'Lưu bài viết'}
          </button>
          <SkinIllustration disease={selected} />
          {selected.icd && (
            <section className="detail-section">
              <h3>Thông tin phân loại</h3>
              <dl className="icd-detail-facts">
                <div>
                  <dt>Nhóm bệnh</dt>
                  <dd>{selected.category}</dd>
                </div>
                <div>
                  <dt>Tên trong nguồn tham khảo</dt>
                  <dd>{selected.icd.title}</dd>
                </div>
              </dl>
            </section>
          )}
          <p className="detail-summary">{selected.summary}</p>
          <ReadingGuide />
          <div className="inline-note">
            <Info size={18} />
            <span>Bản tóm tắt tham khảo, chưa thẩm định lâm sàng. Không dùng để tự chẩn đoán.</span>
          </div>
          <div className="detail-section">
            <h3>Tổng quan</h3>
            <p>{selected.details}</p>
          </div>
          <div className="detail-section">
            <h3>Dấu hiệu được đề cập</h3>
            <div className="chips">
              {selected.symptoms.map((s) => (
                <span key={s.id} className="chip">
                  {s.name}
                </span>
              ))}
            </div>
          </div>
          <div className="detail-section">
            <h3>Yếu tố liên quan</h3>
            <p>{selected.risk_factors}</p>
          </div>
          <div className="detail-section">
            <h3>Phòng ngừa & chăm sóc</h3>
            <p>{selected.prevention}</p>
          </div>
          <div className="detail-section sources-box">
            <h3>
              <ShieldCheck size={18} />
              Nguồn tham khảo
            </h3>
            {selected.references.map((r) => (
              <a key={r.id} href={r.url} target="_blank" rel="noreferrer">
                <span>
                  <strong>{r.title}</strong>
                  <small>
                    {r.publisher} · Truy cập {r.accessed_at}
                  </small>
                </span>
                <ExternalLink size={17} />
              </a>
            ))}
            {selected.icd && (
              <a href={selected.icd.source_url} target="_blank" rel="noreferrer">
                <span>
                  <strong>{selected.icd.title}</strong>
                  <small>World Health Organization · Tài liệu nguồn</small>
                </span>
                <ExternalLink size={17} />
              </a>
            )}
          </div>
          <div className="detail-section">
            <h3>Bài viết liên quan</h3>
            <div className="related-topics">
              {all
                .filter((d) => d.id !== selected.id)
                .map((d) => ({
                  d,
                  score:
                    (d.category === selected.category ? 3 : 0) +
                    d.symptoms.filter((s) => selected.symptoms.some((t) => t.id === s.id)).length,
                }))
                .filter((x) => x.score > 0)
                .sort((a, b) => b.score - a.score)
                .slice(0, 3)
                .map(({ d }) => (
                  <button key={d.id} onClick={() => setSelected(d)}>
                    {d.name}
                    <small>{d.category}</small>
                  </button>
                ))}
            </div>
          </div>
          <small className="muted">
            Phiên bản nội dung {selected.version} ·{' '}
            {selected.review_status === 'editor_reviewed'
              ? 'Đã được biên tập'
              : 'Tóm tắt từ tài liệu nguồn'}
          </small>
        </Modal>
      )}
      {authOpen && (
        <AuthModal
          onClose={() => setAuthOpen(false)}
          onSuccess={(u) => {
            setUser(u);
            setAuthOpen(false);
            setToast('Đã đăng nhập. Bạn có thể chủ động lưu kết quả tra cứu.');
          }}
        />
      )}
      {toast && (
        <div className="toast" role="status" aria-live="polite" aria-atomic="true">
          <span className="toast-icon">
            <Info size={26} />
          </span>
          <div className="toast-content">
            <strong>Thông báo</strong>
            <p>{toast}</p>
          </div>
          <span className="toast-countdown" aria-hidden="true" />
          <button aria-label="Đóng thông báo" onClick={() => setToast('')}>
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}

export let csrf = '';
export function setCsrf(value: string) {
  csrf = value;
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set('Content-Type', 'application/json');
  if (csrf) headers.set('X-CSRF-Token', csrf);
  let res: Response;
  try {
    res = await fetch('/api/v1' + path, { ...options, headers, credentials: 'same-origin' });
  } catch {
    throw new Error('Không kết nối được máy chủ. Vui lòng thử lại.');
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const fields: Record<string, string> = {
      name: 'Tên tiếng Việt',
      english_name: 'Tên tiếng Anh',
      category: 'Nhóm chủ đề',
      summary: 'Tóm tắt',
      details: 'Tổng quan',
      risk_factors: 'Yếu tố liên quan',
      prevention: 'Phòng ngừa & chăm sóc',
      source_title: 'Tên tài liệu nguồn',
      source_url: 'Liên kết nguồn',
      symptom_ids: 'Triệu chứng',
      password: 'Mật khẩu',
      title: 'Tên tài liệu',
      publisher: 'Đơn vị xuất bản',
      content: 'Nội dung',
      usage_note: 'Ghi chú sử dụng',
      email: 'Email',
    };
    if (Array.isArray(data.detail)) {
      const errors = data.detail.map(
        (item: {
          loc?: (string | number)[];
          type?: string;
          ctx?: { min_length?: number; max_length?: number };
          msg?: string;
        }) => {
          const key = String(item.loc?.[1] || '');
          const label = fields[key] || 'Thông tin nhập';
          if (item.type === 'string_too_short')
            return item.ctx?.min_length != null ? `${label}: nhập ít nhất ${item.ctx.min_length} ký tự.` : `${label}: nội dung quá ngắn.`;
          if (item.type === 'string_too_long')
            return item.ctx?.max_length != null ? `${label}: tối đa ${item.ctx.max_length} ký tự.` : `${label}: nội dung quá dài.`;
          if (item.type === 'missing') return `${label}: vui lòng nhập thông tin.`;
          if (item.msg?.startsWith('Value error, ')) return `${label}: ${item.msg.slice(13)}`;
          return `${label}: giá trị chưa hợp lệ.`;
        },
      );
      throw new Error(errors.join(' '));
    }
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : res.status >= 500
          ? 'Máy chủ chưa tải được dữ liệu. Vui lòng thử lại sau.'
          : res.status === 401
            ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
            : 'Thông tin chưa hợp lệ. Vui lòng kiểm tra lại.',
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

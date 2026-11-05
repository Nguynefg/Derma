import { Fragment, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ArrowUp,
  BookOpen,
  Check,
  Copy,
  MessageCircle,
  Plus,
  RotateCcw,
  Sparkles,
  Square,
  X,
} from 'lucide-react';
import { api } from '../../../shared/api/api';
import type { Answer } from '../../../shared/types/documents';

export type ImageChatContext = { observations: string; explanation: string; disease_ids: string[] };
export type ChatTurn = {
  role: 'user' | 'assistant';
  content: string;
  passages?: Answer['passages'];
};

// Render a small Markdown subset as React nodes; never interpret model output as HTML.
function inline(text: string): ReactNode {
  return text
    .split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g)
    .map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : part.startsWith('`') && part.endsWith('`') ? (
        <code key={i}>{part.slice(1, -1)}</code>
      ) : (
        part
      ),
    );
}
function Reply({ text }: { text: string }) {
  const lines = text.split('\n');
  const blocks: ReactNode[] = [];
  for (let i = 0; i < lines.length; ) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    if (/^\s*```/.test(line)) {
      const label = line.trim().slice(3);
      const code: string[] = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) code.push(lines[i++]);
      if (i < lines.length) i++;
      blocks.push(
        <div className="assistant-code" key={i}>
          {label && <small>{label}</small>}
          <pre>
            <code>{code.join('\n')}</code>
          </pre>
        </div>,
      );
    } else if (/^#{1,6}\s/.test(line)) {
      blocks.push(<h3 key={i}>{inline(line.replace(/^#{1,6}\s+/, ''))}</h3>);
      i++;
    } else if (/^\s*(?:[-*+] |\d+[.)] )/.test(line)) {
      const ordered = /^\s*\d+[.)] /.test(line);
      const items: ReactNode[] = [];
      const pattern = ordered ? /^\s*\d+[.)] / : /^\s*[-*+] /;
      while (i < lines.length && pattern.test(lines[i])) {
        items.push(<li key={i}>{inline(lines[i].replace(pattern, ''))}</li>);
        i++;
      }
      blocks.push(ordered ? <ol key={i}>{items}</ol> : <ul key={i}>{items}</ul>);
    } else {
      const paragraph: string[] = [line];
      i++;
      while (
        i < lines.length &&
        lines[i].trim() &&
        !/^\s*(?:```|#{1,6}\s|[-*+] |\d+[.)] )/.test(lines[i])
      )
        paragraph.push(lines[i++]);
      blocks.push(
        <p key={i}>
          {paragraph.map((p, j) => (
            <Fragment key={j}>
              {j > 0 && <br />}
              {inline(p)}
            </Fragment>
          ))}
        </p>,
      );
    }
  }
  return <div className="assistant-reply">{blocks}</div>;
}

export function AssistantChat({
  turns,
  setTurns,
  context,
  clearContext,
  open,
}: {
  turns: ChatTurn[];
  setTurns: (turns: ChatTurn[]) => void;
  context: ImageChatContext | null;
  clearContext: () => void;
  open: (id: string) => void;
}) {
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [copied, setCopied] = useState<number | null>(null);
  const request = useRef<AbortController | null>(null);
  const retry = useRef<{ question: string; history: ChatTurn[] } | null>(null);
  const thread = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const follow = useRef(true);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (follow.current && thread.current)
      thread.current.scrollTop = turns.length || busy ? thread.current.scrollHeight : 0;
  }, [turns, busy]);
  useEffect(() => {
    if (textarea.current) {
      textarea.current.style.height = '0px';
      textarea.current.style.height =
        Math.min(180, Math.max(52, textarea.current.scrollHeight)) + 'px';
    }
  }, [input]);
  useEffect(() => {
    if (copied === null) return;
    const timer = window.setTimeout(() => setCopied(null), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  function stop() {
    request.current?.abort();
    request.current = null;
    setBusy(false);
    setNotice('Đã dừng chờ phản hồi. Bạn có thể gửi tin nhắn khác.');
  }
  function reset() {
    request.current?.abort();
    request.current = null;
    retry.current = null;
    setTurns([]);
    clearContext();
    setInput('');
    setBusy(false);
    setError('');
    setNotice('');
    textarea.current?.focus();
  }
  async function send(value = input, history = turns) {
    const question = value.trim();
    if (request.current || !question || question.length > 4000) return;
    const controller = new AbortController();
    request.current = controller;
    retry.current = { question, history };
    follow.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    setInput('');
    const pending: ChatTurn[] = [...history, { role: 'user', content: question }];
    setTurns(pending);
    try {
      const answer = await api<Answer>('/chat', {
        method: 'POST',
        signal: controller.signal,
        body: JSON.stringify({
          question,
          history: history
            .slice(-12)
            .map(({ role, content }) => ({ role, content: content.slice(0, 4000) })),
          image_context: context,
        }),
      });
      if (controller.signal.aborted || request.current !== controller) return;
      setTurns([
        ...pending,
        { role: 'assistant', content: answer.reply || answer.message, passages: answer.passages },
      ]);
      retry.current = null;
    } catch (e) {
      if (!controller.signal.aborted && request.current === controller)
        setError((e as Error).message);
    } finally {
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }
  async function copy(turn: ChatTurn, index: number) {
    try {
      await navigator.clipboard.writeText(turn.content);
      setCopied(index);
    } catch {
      setNotice('Chưa sao chép được. Bạn có thể chọn và sao chép nội dung trực tiếp.');
    }
  }
  return (
    <section
      className={`assistant-studio ${turns.length ? 'has-conversation' : 'is-welcome'}`}
      aria-label="Trò chuyện với trợ lý AI"
    >
      <header className="assistant-toolbar">
        <div className="assistant-brand">
          <span>
            <Sparkles size={19} />
          </span>
          <div>
            <strong>Derma AI</strong>
            <small>Cùng bạn tìm hiểu mỗi ngày</small>
          </div>
        </div>
        <button className="assistant-new" onClick={reset}>
          <Plus size={17} />
          <span>Cuộc trò chuyện mới</span>
        </button>
      </header>
      {context && (
        <aside className="assistant-image-context">
          <BookOpen size={18} />
          <div>
            <strong>Đang trao đổi về kết quả ảnh</strong>
            <p>
              {context.observations ||
                context.explanation ||
                'Bạn có thể hỏi thêm về các gợi ý trong kết quả.'}
            </p>
          </div>
          <button onClick={clearContext} disabled={busy} aria-label="Bỏ ngữ cảnh ảnh">
            <X size={17} />
          </button>
        </aside>
      )}
      <div
        className="assistant-thread"
        ref={thread}
        role="log"
        aria-label="Nội dung hội thoại"
        aria-live="polite"
        aria-relevant="additions text"
        onScroll={() => {
          const el = thread.current;
          if (el) follow.current = el.scrollHeight - el.scrollTop - el.clientHeight < 90;
        }}
      >
        {!turns.length && (
          <div className="assistant-welcome">
            <div className="assistant-orb">
              <Sparkles size={35} strokeWidth={1.5} />
            </div>
            <span className="assistant-eyebrow">MỘT CÂU HỎI, NHIỀU ĐIỀU SÁNG TỎ</span>
            <h1>
              Hôm nay bạn muốn <span>tìm hiểu điều gì?</span>
            </h1>
            <p>Cùng Derma giải đáp thắc mắc, khám phá sức khỏe và hiểu thêm mỗi ngày.</p>
            <div className="assistant-suggestions">
              {(context
                ? [
                    ['Giải thích kết quả ảnh', 'Giải thích kết quả ảnh này giúp tôi'],
                    ['Tìm hiểu bước tiếp theo', 'Tôi nên lưu ý điều gì sau kết quả ảnh này?'],
                  ]
                : [
                    ['Tìm hiểu sức khỏe', 'Giải thích bệnh vảy nến bằng ngôn ngữ dễ hiểu'],
                    ['Một thói quen tốt hơn', 'Giúp tôi xây dựng thói quen ngủ tốt hơn'],
                    ['Học điều mới', 'Giải thích trí tuệ nhân tạo bằng một ví dụ đơn giản'],
                  ]
              ).map(([title, prompt]) => (
                <button key={title} onClick={() => void send(prompt)}>
                  <MessageCircle size={19} />
                  <strong>{title}</strong>
                  <span>{prompt}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((turn, index) => (
          <article className={'assistant-turn ' + turn.role} key={index}>
            {turn.role === 'assistant' && (
              <div className="assistant-avatar" aria-label="Derma AI">
                <Sparkles size={18} />
              </div>
            )}
            <div className="assistant-turn-body">
              {turn.role === 'user' ? (
                <p className="assistant-user-text">{turn.content}</p>
              ) : (
                <Reply text={turn.content} />
              )}
              {!!turn.passages?.length && (
                <div className="assistant-references">
                  <span>
                    <BookOpen size={14} /> Bài viết liên quan
                  </span>
                  <div>
                    {turn.passages.map((p, i) => (
                      <button key={p.document_id} onClick={() => open(p.disease_id)}>
                        [{i + 1}] {p.disease_name}
                      </button>
                    ))}
                  </div>
                  <details>
                    <summary>Xem nguồn tham khảo</summary>
                    {turn.passages.map((p) => (
                      <a key={p.document_id} href={p.source_url} target="_blank" rel="noreferrer">
                        {p.publisher} · {p.title}
                      </a>
                    ))}
                  </details>
                </div>
              )}
              {turn.role === 'assistant' && (
                <div className="assistant-actions">
                  <button onClick={() => void copy(turn, index)} aria-label="Sao chép câu trả lời">
                    {copied === index ? <Check size={15} /> : <Copy size={15} />}
                    {copied === index ? 'Đã sao chép' : 'Sao chép'}
                  </button>
                  {index === turns.length - 1 && index > 0 && turns[index - 1].role === 'user' && (
                    <button
                      disabled={busy}
                      onClick={() => void send(turns[index - 1].content, turns.slice(0, index - 1))}
                    >
                      <RotateCcw size={15} /> Trả lời lại
                    </button>
                  )}
                </div>
              )}
            </div>
          </article>
        ))}
        {busy && (
          <div className="assistant-thinking" role="status">
            <Sparkles size={18} />
            <span>Đang soạn câu trả lời</span>
            <i />
            <i />
            <i />
          </div>
        )}
        {error && (
          <div className="assistant-error" role="alert">
            <p>{error}</p>
            <button
              onClick={() => {
                if (retry.current) void send(retry.current.question, retry.current.history);
              }}
            >
              <RotateCcw size={15} /> Thử lại
            </button>
          </div>
        )}
      </div>
      <footer className="assistant-input-area">
        <form
          className="assistant-input-box"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <textarea
            ref={textarea}
            aria-label="Tin nhắn cho trợ lý"
            placeholder="Hỏi Derma bất cứ điều gì…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={4000}
            rows={1}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                if (!busy) void send();
              }
            }}
          />
          <div className="assistant-input-bottom">
            <span>
              <Sparkles size={14} /> Trợ lý AI <small>· {input.length}/4000</small>
            </span>
            {busy ? (
              <button
                type="button"
                className="assistant-send"
                onClick={stop}
                aria-label="Dừng chờ phản hồi"
              >
                <Square size={17} fill="currentColor" />
              </button>
            ) : (
              <button
                type="submit"
                className="assistant-send"
                disabled={!input.trim()}
                aria-label="Gửi tin nhắn"
              >
                <ArrowUp size={21} />
              </button>
            )}
          </div>
        </form>
        <div className="assistant-footnote">
          <span>
            AI có thể mắc lỗi. Hãy kiểm tra thông tin quan trọng; thông tin sức khỏe không thay thế
            việc khám bệnh.
          </span>
          <small>Hội thoại chỉ giữ trong phiên này · Nội dung được gửi đến dịch vụ AI</small>
        </div>
        {notice && (
          <p className="assistant-notice" role="status">
            {notice}
          </p>
        )}
      </footer>
    </section>
  );
}

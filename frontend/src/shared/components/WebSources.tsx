export type WebSource = { title: string; url: string };

export function WebSources({
  sources = [],
  suggestions = '',
}: {
  sources?: WebSource[];
  suggestions?: string;
}) {
  const safe = sources.filter((source) => {
    try {
      const url = new URL(source.url);
      return url.protocol === 'https:' && !url.username && !url.password;
    } catch {
      return false;
    }
  });
  if (!safe.length && !suggestions) return null;
  return (
    <section className="web-sources" aria-label="Nguồn web tham khảo">
      <strong>Nguồn web tham khảo</strong>
      <p>Thông tin ngoài thư viện, do AI tổng hợp. Hãy mở nguồn để đối chiếu.</p>
      <div>
        {safe.map((source, index) => (
          <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">
            {index + 1}. {source.title} ↗
          </a>
        ))}
      </div>
      {suggestions && (
        <iframe
          title="Gợi ý tìm kiếm Google"
          srcDoc={suggestions}
          sandbox="allow-popups allow-popups-to-escape-sandbox"
          referrerPolicy="no-referrer"
        />
      )}
    </section>
  );
}

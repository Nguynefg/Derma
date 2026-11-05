import { PageHeading } from './Decor';

export function Heading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  const variant = eyebrow.includes('TRIỆU CHỨNG')
    ? 'symptoms'
    : eyebrow.includes('HÌNH ẢNH')
      ? 'images'
      : eyebrow.includes('NGUỒN')
        ? 'sources'
        : eyebrow.includes('CỦA BẠN')
          ? 'history'
          : eyebrow.includes('QUẢN TRỊ')
            ? 'admin'
            : 'library';
  return (
    <PageHeading eyebrow={eyebrow} title={title} description={description} variant={variant} />
  );
}

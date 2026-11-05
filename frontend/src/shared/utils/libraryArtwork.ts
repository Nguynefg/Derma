
type ArtworkEntry = {
  id: string;
  title: string;
  category: string;
  article?: { specialty?: string };
  icd?: { chapter?: string };
};

const specialties: Record<string, string> = {
  '05': 'Nội tiết, dinh dưỡng & chuyển hóa',
  '08': 'Thần kinh',
  '09': 'Mắt & thị giác',
  '10': 'Tai mũi họng',
  '11': 'Tim mạch',
  '12': 'Hô hấp',
  '13': 'Tiêu hóa',
  '14': 'Da liễu',
  '15': 'Cơ xương khớp',
  '16': 'Tiết niệu & sinh dục',
  '18': 'Sản khoa',
  '19': 'Chu sinh',
};

/** Every article gets a stable individual cover; these are decorative, not clinical images. */
export function libraryArtwork(entry: ArtworkEntry, category: string) {
  const text = category
    .toLowerCase()
    .replace(/đ/g, 'd')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
  let theme = 'general';
  let label = entry.article?.specialty || specialties[entry.icd?.chapter || ''] || category;
  if (/vac[- ]?xin|vaccine/.test(text)) {
    theme = 'vaccines';
    label = 'Vắc-xin';
  } else if (entry.article?.specialty === 'Da liễu' || entry.icd?.chapter === '14') {
    theme = 'dermatology';
    label = 'Da liễu';
  } else if (/\b(thuoc|hoat chat|che pham|duoc chat|duoc pham|drug|pharmaceutical)\b/.test(text)) {
    theme = 'molecules';
    label = 'Hoạt chất & chế phẩm';
  } else if (label.length > 44) {
    label = entry.icd?.chapter === 'X' ? 'Kiến thức bổ sung' : 'Kiến thức sức khỏe';
  }
  return { theme, label, groupTitle: category };
}

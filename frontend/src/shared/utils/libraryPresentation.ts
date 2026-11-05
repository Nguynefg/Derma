type LibraryEntry = {
  type: 'article' | 'icd';
  title: string;
  category: string;
  summary: string;
  icd?: { chapter?: string; chapter_title?: string; group_name?: string; original_title?: string };
};

const supplementalGroups: Record<string, string> = {
  '25': 'Thông tin sức khỏe đặc biệt',
  '26': 'Y học cổ truyền',
  V: 'Đánh giá chức năng',
  X: 'Kiến thức bổ sung',
};

export function hasLibraryContent(value?: string) {
  return Boolean(value?.trim()) &&
    !/^(Thông tin tóm tắt|Nội dung tổng quan) đang được bổ sung\.?$|^Chưa bổ sung thông tin về /.test(value!.trim());
}

// Explain the source entry's scope without inventing a clinical definition.
export function libraryScope(chapter: string | undefined, category: string) {
  if (chapter === 'X') {
    if (/thang|thang đo|giai đoạn|NYHA|GOLD|cường độ đau|mức độ vấn đề/i.test(category))
      return { label: 'Thang đánh giá', text: `Một mức hoặc tiêu chí trong nhóm ${category.toLocaleLowerCase('vi')}. Cần đọc cùng thang đánh giá tương ứng để hiểu ý nghĩa.`, supplemental: true };
    if (/thuốc|hoạt chất|chế phẩm|vắc.?xin|hóa chất|chất .*quang/i.test(category))
      return { label: 'Hoạt chất & chế phẩm', text: `Tên tra cứu thuộc nhóm ${category.toLocaleLowerCase('vi')}. Danh pháp quốc tế được giữ để đối chiếu chính xác; mục này chưa có chuyên luận về công dụng và cách sử dụng.`, supplemental: true };
    if (/tác nhân|mầm bệnh|giun|động vật nguyên sinh|chấy|vi khuẩn|vi.?rút/i.test(category))
      return { label: 'Tác nhân & sinh vật', text: `Tên khoa học trong nhóm ${category.toLocaleLowerCase('vi')}. Tên tác nhân được giữ theo danh pháp để tra cứu và đối chiếu tài liệu.`, supplemental: true };
    return { label: 'Thuật ngữ bổ sung', text: `Thuật ngữ thuộc nhóm ${category.toLocaleLowerCase('vi')}, dùng để mô tả và bổ sung thông tin chuyên môn. Đây không phải một bài bệnh lý độc lập.`, supplemental: true };
  }
  if (chapter === 'V')
    return { label: 'Đánh giá chức năng', text: 'Nội dung mô tả chức năng và khả năng hoạt động. Cần đọc cùng bối cảnh đánh giá; tên mục không phải kết luận bệnh.', supplemental: true };
  return { label: 'Thông tin sức khỏe', text: `Chủ đề thuộc nhóm ${category.toLocaleLowerCase('vi')}. Hiện mới có thông tin tên và nhóm chủ đề; chưa có bài tổng quan để đọc.`, supplemental: false };
}

// Older running servers can still return import labels until they are restarted.
export function libraryPresentation(entry: LibraryEntry) {
  const legacyCategory = /^ICD[\s-]*11\s+(\S+)$/i.exec(entry.category.trim());
  const chapter = entry.icd?.chapter || legacyCategory?.[1];
  const explicitGroup =
    entry.icd?.group_name === 'Giải phẫu, hoạt chất và thông tin bổ sung'
      ? undefined
      : entry.icd?.group_name;
  const category =
    explicitGroup ||
    (chapter && supplementalGroups[chapter]
      ? supplementalGroups[chapter]
      : entry.icd?.chapter_title || (legacyCategory ? 'Kiến thức sức khỏe' : entry.category));
  const imported = entry.type === 'icd' || Boolean(legacyCategory);
  const summaryPending =
    imported &&
    (!entry.summary.trim() ||
      /^(Tìm hiểu .*Nhóm chủ đề:|Mục phân loại|Nhóm phân loại|Chương\s)/s.test(entry.summary) ||
      entry.summary === 'Thông tin tóm tắt đang được bổ sung.');
  return {
    ...libraryScope(chapter, category),
    scientificName: chapter === 'X' && entry.icd?.original_title === entry.title,
    title: chapter === 'X' && category === 'Giá trị thang đo vấn đề'
      ? ({'0 Không có vấn đề':'Không có vấn đề (mức 0)', '1 Vấn đề nhẹ':'Vấn đề mức độ nhẹ (mức 1)', '2 Vấn đề vừa':'Vấn đề mức độ vừa (mức 2)', '3 Vấn đề nặng':'Vấn đề mức độ nặng (mức 3)', '4 Vấn đề hoàn toàn':'Vấn đề ở mức hoàn toàn (mức 4)', '9 Không áp dụng':'Không áp dụng (mã 9)'} as Record<string,string>)[entry.title] || entry.title
      : entry.title,
    category: entry.type === 'article' && !legacyCategory ? entry.category : category,
    summary: summaryPending ? libraryScope(chapter, category).text : entry.summary,
    summaryPending,
  };
}

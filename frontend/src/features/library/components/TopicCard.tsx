import { DiseaseCover } from '../../../shared/components/DiseaseCover';
import { ArrowRight, ArrowUpRight, BookOpen, Check, FileText } from 'lucide-react';
import type { Disease } from '../../../shared/types/index';

export function TopicCard({
  disease,
  index = 0,
  open,
}: {
  disease: Disease;
  index?: number;
  open: () => void;
}) {
  return (
    <article className={'disease-card topic-tone-' + (index % 3)}>
      <DiseaseCover name={disease.name} englishName={disease.english_name} />
      <div className="topic-card-top">
        <span className={'topic-icon topic-color-' + (index % 3)}>
          <BookOpen size={23} />
        </span>
        <span className="category-badge">
          {disease.specialty === 'Da liễu'
            ? disease.category
            : disease.specialty || disease.category}
        </span>
        <ArrowUpRight className="topic-card-arrow" size={20} />
      </div>
      <div className="card-body">
        <h3><button className="topic-name-button" onClick={open}>{disease.name}</button></h3>
        <span className="english-name">{disease.english_name}</span>
        <p>{disease.summary}</p>
        {disease.matched_symptoms ? (
          <div className="matched">
            <Check size={16} />
            <span>Dấu hiệu được đề cập: {disease.matched_symptoms.join(', ')}</span>
          </div>
        ) : null}
      </div>
      <div className="card-bottom">
        <span>
          <FileText size={15} />
          {disease.references.length} nguồn tham khảo
        </span>
        <button className="topic-read-button" onClick={open}>
          Đọc thông tin <ArrowRight size={16} />
        </button>
      </div>
    </article>
  );
}


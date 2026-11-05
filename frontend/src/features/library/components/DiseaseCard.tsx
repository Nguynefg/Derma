import type { Disease } from '../../../shared/types/index';
import { TopicCard } from './TopicCard';

export function DiseaseCard({
  disease,
  index,
  open,
}: {
  disease: Disease;
  index: number;
  open: () => void;
}) {
  return <TopicCard disease={disease} index={index} open={open} />;
}

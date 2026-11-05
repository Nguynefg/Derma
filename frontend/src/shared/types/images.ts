export type ModelState = {
  status: string;
  message: string;
  image_type?: string;
  label_count?: number;
  version?: string | null;
  classification_unit?: 'disease' | 'group';
  data_limitations?: string[];
};

export type CatalogCoverage = {
  published_topics: number;
  mapped_topics: number;
  mapping_valid: boolean;
  mapped_labels: { disease_id: string; name: string }[];
  notice: string;
};

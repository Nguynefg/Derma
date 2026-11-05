export type Symptom = { id: string; name: string; specialties?: string[] };
export type Reference = {
  id: string;
  slug: string;
  title: string;
  publisher: string;
  url: string;
  accessed_at: string;
  usage_note: string;
};
export type Disease = {
  id: string;
  code: string;
  icd?: {
    id: string;
    title: string;
    code: string | null;
    chapter: string;
    source_url: string;
  } | null;
  slug: string;
  name: string;
  english_name: string;
  category: string;
  specialty: string;
  photo_supported: boolean;
  summary: string;
  details: string;
  risk_factors: string;
  prevention: string;
  aliases: string[];
  published: boolean;
  review_status: string;
  version: number;
  updated_at: string;
  symptoms: Symptom[];
  references: Reference[];
  matched_symptoms?: string[];
  match_count?: number;
};
export type User = { id: string; name: string; email: string; role: string };
export type HistoryItem = {
  id: string;
  mode: string;
  query: string;
  created_at: string;
  results: { id: string; name: string; version: number }[];
};

export type Page =
  | 'home'
  | 'library'
  | 'questions'
  | 'symptoms'
  | 'images'
  | 'history'
  | 'sources'
  | 'profile'
  | 'admin';
export type SearchResult = { items: Disease[]; total?: number; notice?: string };

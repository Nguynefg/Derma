export type ParsedSymptom = {
  id: string;
  name: string;
  presence: 'present' | 'absent' | 'unknown';
  requires_confirmation: boolean;
};
export type Passage = {
  document_id: string;
  document_version: number;
  title: string;
  content: string;
  source_url: string;
  publisher: string;
  usage_note: string;
  disease_id: string;
  disease_name: string;
  checksum: string;
};
export type Answer = {
  reply?: string;
  status: 'supported' | 'insufficient_evidence' | 'out_of_scope' | 'general' | 'external_result';
  message: string;
  method: string;
  passages: Passage[];
  external_sources?: { title: string; url: string }[];
  search_suggestions_html?: string;
  fallback?: { status: string; message?: string };
};
export type Doc = {
  id: string;
  disease_id: string;
  title: string;
  publisher: string;
  source_url: string;
  usage_note: string;
  published: boolean;
  version: number;
  content: string;
  checksum: string;
};
export type DocForm = Omit<Doc, 'id' | 'version' | 'checksum'> & {
  expected_version: number | null;
};

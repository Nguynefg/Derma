-- Generated from SQLAlchemy models. Initial schema, not a migration.


CREATE TABLE tbldiseases (
	disease_id INTEGER NOT NULL IDENTITY, 
	slug NVARCHAR(60) NOT NULL, 
	name NVARCHAR(120) NOT NULL, 
	english_name NVARCHAR(120) NOT NULL, 
	category NVARCHAR(60) NOT NULL, 
	summary NVARCHAR(max) NOT NULL, 
	details NVARCHAR(max) NOT NULL, 
	risk_factors NVARCHAR(max) NOT NULL, 
	prevention NVARCHAR(max) NOT NULL, 
	aliases NVARCHAR(max) NOT NULL, 
	published BIT NOT NULL, 
	review_status NVARCHAR(40) NOT NULL, 
	version INTEGER NOT NULL, 
	updated_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (disease_id), 
	UNIQUE (slug)
)

;


CREATE TABLE tbllibrary_updates (
	update_id NVARCHAR(100) NOT NULL, 
	applied_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (update_id)
)

;


CREATE TABLE tblsymptoms (
	symptom_id INTEGER NOT NULL IDENTITY, 
	slug NVARCHAR(50) NOT NULL, 
	name NVARCHAR(80) NOT NULL, 
	PRIMARY KEY (symptom_id), 
	UNIQUE (slug)
)

;


CREATE TABLE tblusers (
	user_id INTEGER NOT NULL IDENTITY, 
	legacy_id NVARCHAR(36) NOT NULL, 
	email NVARCHAR(254) NOT NULL, 
	name NVARCHAR(80) NOT NULL, 
	password_hash NVARCHAR(max) NOT NULL, 
	role NVARCHAR(20) NOT NULL, 
	created_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (user_id), 
	UNIQUE (legacy_id), 
	UNIQUE (email)
)

;


CREATE TABLE tbladmin_audit_logs (
	audit_id INTEGER NOT NULL IDENTITY, 
	legacy_id NVARCHAR(36) NOT NULL, 
	actor_id INTEGER NOT NULL, 
	action NVARCHAR(80) NOT NULL, 
	entity_id NVARCHAR(80) NOT NULL, 
	snapshot NVARCHAR(max) NOT NULL, 
	created_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (audit_id), 
	UNIQUE (legacy_id), 
	FOREIGN KEY(actor_id) REFERENCES tblusers (user_id)
)

;


CREATE TABLE tblbookmarks (
	user_id INTEGER NOT NULL, 
	disease_id INTEGER NOT NULL, 
	created_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (user_id, disease_id), 
	FOREIGN KEY(user_id) REFERENCES tblusers (user_id) ON DELETE CASCADE, 
	FOREIGN KEY(disease_id) REFERENCES tbldiseases (disease_id) ON DELETE CASCADE
)

;


CREATE TABLE tbldisease_symptoms (
	disease_id INTEGER NOT NULL, 
	symptom_id INTEGER NOT NULL, 
	PRIMARY KEY (disease_id, symptom_id), 
	FOREIGN KEY(disease_id) REFERENCES tbldiseases (disease_id) ON DELETE CASCADE, 
	FOREIGN KEY(symptom_id) REFERENCES tblsymptoms (symptom_id)
)

;


CREATE TABLE tblimage_records (
	image_id INTEGER NOT NULL IDENTITY, 
	file_uuid NVARCHAR(36) NOT NULL, 
	user_id INTEGER NOT NULL, 
	disease_id INTEGER NULL, 
	pixel_sha256 NVARCHAR(64) NOT NULL, 
	image_type NVARCHAR(20) NOT NULL, 
	width INTEGER NOT NULL, 
	height INTEGER NOT NULL, 
	is_reference BIT NOT NULL, 
	consent_version NVARCHAR(30) NOT NULL, 
	created_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (image_id), 
	UNIQUE (file_uuid), 
	FOREIGN KEY(user_id) REFERENCES tblusers (user_id), 
	FOREIGN KEY(disease_id) REFERENCES tbldiseases (disease_id)
)

;

CREATE INDEX ix_tblimage_records_pixel_sha256 ON tblimage_records (pixel_sha256);


CREATE TABLE tblmedical_documents (
	document_id INTEGER NOT NULL IDENTITY, 
	slug NVARCHAR(80) NOT NULL, 
	disease_id INTEGER NOT NULL, 
	title NVARCHAR(200) NOT NULL, 
	publisher NVARCHAR(150) NOT NULL, 
	source_url NVARCHAR(max) NOT NULL, 
	usage_note NVARCHAR(max) NOT NULL, 
	published BIT NOT NULL, 
	version INTEGER NOT NULL, 
	updated_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (document_id), 
	UNIQUE (slug), 
	FOREIGN KEY(disease_id) REFERENCES tbldiseases (disease_id) ON DELETE CASCADE
)

;


CREATE TABLE tblmedical_references (
	reference_id INTEGER NOT NULL IDENTITY, 
	slug NVARCHAR(80) NOT NULL, 
	disease_id INTEGER NOT NULL, 
	title NVARCHAR(200) NOT NULL, 
	publisher NVARCHAR(150) NOT NULL, 
	url NVARCHAR(max) NOT NULL, 
	accessed_at NVARCHAR(10) NOT NULL, 
	usage_note NVARCHAR(max) NOT NULL, 
	PRIMARY KEY (reference_id), 
	UNIQUE (slug), 
	FOREIGN KEY(disease_id) REFERENCES tbldiseases (disease_id) ON DELETE CASCADE
)

;


CREATE TABLE tblsearch_history (
	history_id INTEGER NOT NULL IDENTITY, 
	legacy_id NVARCHAR(36) NOT NULL, 
	user_id INTEGER NOT NULL, 
	mode NVARCHAR(20) NOT NULL, 
	query NVARCHAR(300) NOT NULL, 
	results NVARCHAR(max) NOT NULL, 
	consent_version NVARCHAR(30) NOT NULL, 
	created_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (history_id), 
	UNIQUE (legacy_id), 
	FOREIGN KEY(user_id) REFERENCES tblusers (user_id) ON DELETE CASCADE
)

;


CREATE TABLE tblsessions (
	token_hash NVARCHAR(64) NOT NULL, 
	user_id INTEGER NOT NULL, 
	csrf NVARCHAR(64) NOT NULL, 
	expires_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES tblusers (user_id) ON DELETE CASCADE
)

;


CREATE TABLE tbldocument_versions (
	document_version_id INTEGER NOT NULL IDENTITY, 
	legacy_id NVARCHAR(36) NOT NULL, 
	document_id INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	title NVARCHAR(200) NOT NULL, 
	publisher NVARCHAR(150) NOT NULL, 
	source_url NVARCHAR(max) NOT NULL, 
	usage_note NVARCHAR(max) NOT NULL, 
	content NVARCHAR(max) NOT NULL, 
	checksum NVARCHAR(64) NOT NULL, 
	editor_id INTEGER NULL, 
	created_at DATETIMEOFFSET NOT NULL, 
	PRIMARY KEY (document_version_id), 
	UNIQUE (legacy_id), 
	FOREIGN KEY(document_id) REFERENCES tblmedical_documents (document_id) ON DELETE CASCADE, 
	FOREIGN KEY(editor_id) REFERENCES tblusers (user_id)
)

;
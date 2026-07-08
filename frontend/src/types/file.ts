/** Metadata for a single uploaded file. */
export interface FileItem {
  /** Unique file identifier (UUID4). */
  id: string
  /** Original filename with extension. */
  filename: string
  /** File size in bytes. */
  size_bytes: number
  /** MIME type of the file. */
  content_type: string
  /** Upload timestamp (UTC, ISO 8601). */
  uploaded_at: string
}

/** List of uploaded files with total count. */
export interface FileListResponse {
  /** List of file metadata. */
  files: FileItem[]
  /** Total number of uploaded files. */
  total: number
}

/** Response after uploading one or more files. */
export interface FileUploadResponse {
  /** Metadata of uploaded files. */
  files: FileItem[]
  /** Total number of uploaded files. */
  total: number
  /** Human-readable confirmation. */
  message: string
}

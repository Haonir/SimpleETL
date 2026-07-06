/** Supported UI language codes. */
export type Language = "en" | "ru"

/** Output format for generated markdown files. */
export type OutputFormat = "spr" | "frontmatter" | "markdown" | "html"

/** LLM provider configuration (model name, base URL, API key). */
export interface LLMConfig {
  /** Name of the LLM model. */
  model: string
  /** Base URL of the OpenAI-compatible endpoint. */
  base_url: string
  /** API key for authentication with the LLM provider. */
  api_key: string
}

/** ETL processing parameters (chunking, workers, output format). */
export interface ProcessingConfig {
  /** Max tokens/characters per chunk. */
  chunk_size: number
  /** Overlap between adjacent chunks. */
  chunk_overlap: number
  /** Number of parallel processing workers. */
  max_workers: number
  /** Output format for generated markdown files. */
  output_format: OutputFormat
  /** Skip LLM processing — chunks are packed directly. */
  skip_llm: boolean
  /** Enable OCR processing for images and scanned PDFs. */
  ocr_enabled: boolean
  /** Tesseract OCR languages (e.g. 'rus+eng', 'eng'). */
  ocr_languages: string
}

/** A single prompt entry in the library (name + text). */
export interface PromptEntry {
  /** Unique prompt identifier. */
  name: string
  /** Prompt template text. */
  text: string
}

/** Full configuration response (LLM + processing + prompts). */
export interface ConfigResponse {
  llm: LLMConfig
  processing: ProcessingConfig
  prompts: PromptEntry[]
  /** Name of the currently active prompt. */
  current_prompt_name: string
  /** UI language code. */
  language: Language
}

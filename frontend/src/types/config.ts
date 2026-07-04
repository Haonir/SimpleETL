/** Output format for generated markdown files. */
export type OutputFormat = "spr" | "frontmatter" | "markdown"

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
}

/** Partial configuration update (all fields optional for PATCH semantics). */
export interface ConfigUpdateRequest {
  llm?: LLMConfig
  processing?: ProcessingConfig
  prompts?: PromptEntry[]
  current_prompt_name?: string
}

/** Request body for creating a new prompt in the library. */
export interface PromptCreateRequest {
  name: string
  text: string
}

/** Confirmation response after deleting a prompt by name. */
export interface PromptDeleteResponse {
  /** Name of the deleted prompt. */
  deleted: string
  /** Human-readable confirmation. */
  message: string
}

/** List of all prompts in the library with total count. */
export interface PromptLibraryResponse {
  prompts: PromptEntry[]
  /** Total number of prompts in the library. */
  total: number
}

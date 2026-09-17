import { ApiError } from "../types/detector"

// Vite exposes env vars prefixed VITE_ on import.meta.env at build time.
// Falls back to localhost:8000 (the backend's default uvicorn port) for
// local dev if the env var isn't set.
const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000"

const CLIENT_TIMEOUT_MS = 90_000 // generous -- Deep mode + a slow model call can legitimately take a while

interface RequestOptions {
  method?: "GET" | "POST"
  body?: unknown
  timeoutMs?: number
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, timeoutMs = CLIENT_TIMEOUT_MS } = options

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch (err) {
    clearTimeout(timer)
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("timeout", "The request took too long and was cancelled.")
    }
    throw new ApiError("network", "Could not reach the verification service.")
  }
  clearTimeout(timer)

  if (!response.ok) {
    throw await toApiError(response)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError("unknown", "The server returned a response that couldn't be read.")
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let bodyMessage: string | undefined
  try {
    const data = await response.json()
    // FastAPI validation errors: {"detail": [{"msg": ...}, ...]}
    // Our custom error handlers: {"error": "..."}
    if (typeof data?.error === "string") {
      bodyMessage = data.error
    } else if (Array.isArray(data?.detail) && data.detail.length > 0) {
      bodyMessage = data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ")
    } else if (typeof data?.detail === "string") {
      bodyMessage = data.detail
    }
  } catch {
    // body wasn't JSON -- fall through with no extra detail
  }

  switch (response.status) {
    case 422:
      return new ApiError("validation", bodyMessage ?? "Please check your input.", 422)
    case 413:
      return new ApiError("payload_too_large", bodyMessage ?? "That input is too large.", 413)
    case 429: {
      const retryAfter = Number(response.headers.get("Retry-After"))
      return new ApiError(
        "rate_limited",
        bodyMessage ?? "Too many requests -- please slow down.",
        429,
        Number.isFinite(retryAfter) ? retryAfter : undefined
      )
    }
    case 504:
      return new ApiError("server_timeout", bodyMessage ?? "The analysis timed out.", 504)
    case 500:
      return new ApiError("server_error", bodyMessage ?? "Something went wrong on the server.", 500)
    default:
      return new ApiError("unknown", bodyMessage ?? `Unexpected error (${response.status}).`, response.status)
  }
}

export { BASE_URL }

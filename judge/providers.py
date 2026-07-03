"""Unified LLM-judge provider interface. Keys loaded from the local md file at runtime.
NEVER prints or persists keys. Returns (text, raw_meta)."""
import os, re, json, time, urllib.request, urllib.error

# Path to a local, git-ignored file holding `PROVIDER_API_KEY = value` lines.
# Override with the MEDROBUST_KEYS_PATH env var; defaults to API_KEYS.local.md next to the repo root.
KEYS_PATH = os.environ.get(
    "MEDROBUST_KEYS_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "API_KEYS.local.md"),
)

def load_keys(path=KEYS_PATH):
    txt = open(path).read()
    keys = {}
    for m in re.finditer(r'^([A-Z_]+_API_KEY)\s*=\s*(\S+)', txt, re.M):
        keys[m.group(1)] = m.group(2).strip()
    return keys

def _post(url, headers, payload, timeout=180):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        return e.code, {"__error__": body}
    except Exception as e:
        return -1, {"__error__": repr(e)[:500]}

# ---- model IDs (best-guess for 2026; adjust after connectivity test) ----
MODELS = {
    "gpt-5.5":        dict(provider="openai",    model="gpt-5.5"),
    "opus-4.8":       dict(provider="anthropic", model="claude-opus-4-8"),
    "grok-4.3":       dict(provider="xai",       model="grok-4.3"),
    "gemini-3.5-flash": dict(provider="google",  model="gemini-3.5-flash"),
}

def call(judge, system, user, keys, high=True, max_tokens=2000):
    cfg = MODELS[judge]; p = cfg["provider"]; model = cfg["model"]
    if p == "openai":
        h = {"Authorization": f"Bearer {keys['OPENAI_API_KEY']}", "Content-Type": "application/json"}
        payload = {"model": model,
                   "messages": [{"role":"system","content":system},{"role":"user","content":user}]}
        if high: payload["reasoning_effort"] = "high"
        payload["max_completion_tokens"] = max_tokens + (6000 if high else 0)
        st, r = _post("https://api.openai.com/v1/chat/completions", h, payload)
        if "__error__" in r: return None, r
        u = r.get("usage", {}) or {}
        reas = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
        return r["choices"][0]["message"]["content"], {"status":st,"reasoning_tokens":reas,"usage":u}
    if p == "xai":
        h = {"Authorization": f"Bearer {keys['XAI_API_KEY']}", "Content-Type": "application/json"}
        payload = {"model": model,
                   "messages": [{"role":"system","content":system},{"role":"user","content":user}]}
        if high: payload["reasoning_effort"] = "high"
        st, r = _post("https://api.x.ai/v1/chat/completions", h, payload)
        if "__error__" in r: return None, r
        u = r.get("usage", {}) or {}
        reas = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
        return r["choices"][0]["message"]["content"], {"status":st,"reasoning_tokens":reas,"usage":u}
    if p == "anthropic":
        h = {"x-api-key": keys["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
             "Content-Type": "application/json"}
        payload = {"model": model, "max_tokens": max_tokens + (8000 if high else 0),
                   "system": system, "messages": [{"role":"user","content":user}]}
        if high:
            payload["thinking"] = {"type":"adaptive"}
            payload["output_config"] = {"effort":"high"}
        st, r = _post("https://api.anthropic.com/v1/messages", h, payload)
        if "__error__" in r: return None, r
        txt = "".join(b.get("text","") for b in r.get("content",[]) if b.get("type")=="text")
        has_think = any(b.get("type")=="thinking" for b in r.get("content",[]))
        return txt, {"status":st,"thinking_block_present":has_think,"usage":r.get("usage",{})}
    if p == "google":
        key = keys["GOOGLE_API_KEY"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        h = {"Content-Type": "application/json"}
        payload = {"systemInstruction":{"parts":[{"text":system}]},
                   "contents":[{"role":"user","parts":[{"text":user}]}],
                   "generationConfig":{"maxOutputTokens": max_tokens + (6000 if high else 0)}}
        if high: payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 6000}
        st, r = _post(url, h, payload)
        if "__error__" in r: return None, r
        try:
            txt = "".join(p.get("text","") for p in r["candidates"][0]["content"]["parts"])
        except Exception:
            return None, {"__error__": json.dumps(r)[:500]}
        um = r.get("usageMetadata", {}) or {}
        return txt, {"status":st,"thoughts_token_count":um.get("thoughtsTokenCount"),"usage":um}
    raise ValueError(judge)

if __name__ == "__main__":
    keys = load_keys()
    print("keys loaded:", sorted(keys.keys()))  # names only, never values
    for judge in MODELS:
        t0=time.time()
        txt, meta = call(judge, "You are a test.", "Reply with exactly one word: pong", keys, high=True, max_tokens=50)
        dt=time.time()-t0
        if txt is None:
            print(f"  [FAIL] {judge:16s} ({MODELS[judge]['model']}): {meta}")
        else:
            print(f"  [ OK ] {judge:16s} ({MODELS[judge]['model']}): {txt.strip()[:60]!r}  ({dt:.1f}s)")

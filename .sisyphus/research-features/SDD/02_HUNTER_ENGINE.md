# HUNTER ENGINE SPECIFICATION

**Module:** Hunter / Core Logic  
**Focus:** Strategies and Extraction

---

## 1. UNIVERSAL EXTRACTOR (`app/hunter/extractor.py`)

The Extractor is the brain. It takes raw bytes and returns a list of `Proxy` objects.

### 1.1. Decoding Pipeline
The content passes through a chain of decoders until proxies are found:
1.  **Plain Text:** Check for `IP:Port` patterns.
2.  **Base64:** Try `base64.b64decode`. If valid, recurse to Step 1.
3.  **HTML/Soup:** If HTML tags present, strip tags and recurse to Step 1.
4.  **SIP002/VMess:** Detect `ss://`, `vmess://`, `trojan://` URIs and parse them using `app/utils/uri_parser.py`.

### 1.2. Regex Patterns
- **IPv4:Port:** `r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b"`
- **Protocol URI:** `r"(vmess|vless|ss|trojan)://[a-zA-Z0-9+/=]+"`

---

## 2. DISCOVERY STRATEGIES

### 2.1. GitHub Strategy (`app/hunter/strategies/github.py`)
- **API:** `https://api.github.com/search/code` (Unauthenticated rate limit: 10/min).
- **Queries:**
  - `filename:proxy.txt pushed:>24h`
  - `extension:yaml "proxies" pushed:>24h`
- **Logic:**
  1.  Search for files.
  2.  Filter by size (< 5MB).
  3.  Return `raw.githubusercontent.com` URLs.

### 2.2. AI Strategy (`app/hunter/strategies/ai.py`)
- **Provider:** `g4f` (GPT4Free) or HuggingFace Interface.
- **Method:** `ask_ai(prompt: str) -> List[str]`
- **Prompt:**
  > "Find me 5 public URLS for free proxy lists updated in the last 24 hours. They should be GitHub, Pastebin, or similar raw text URLs. Return ONLY the URLs as a JSON list."

### 2.3. Search Strategy (`app/hunter/strategies/search.py`)
- **Engine:** Google / DuckDuckGo.
- **Routing:** **MUST** use `app.db_storage.get_random_proxy()` to rotate IPs.
- **Queries:**
  - `intitle:"proxy list" site:pastebin.com`
  - `intext:"vmess://" "2026"`

---

## 3. SCORING HEURISTICS
A candidate receives a `confidence_score` (0-100) based on:
- **+20**: Domain is trusted (github, gitlab, pastebin).
- **+30**: Extractor found > 50 proxies.
- **+20**: Extractor found > 3 distinct protocols.
- **+30**: Initial sample validation (try 5 random proxies) had > 20% success.

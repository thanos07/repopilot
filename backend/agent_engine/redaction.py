import re

PATTERNS=[re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),re.compile(r"(?i)\b(?:password|api[_-]?key|client[_-]?secret)\s*[:=]\s*[^\s,;]+"),re.compile(r'\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,})\b'),re.compile(r'(?i)(authorization\s*[:=]\s*["\x27]?bearer\s+)[^\s"\x27]+')]
def redact(value):
    if isinstance(value,dict):return {k:('[REDACTED]' if str(k).lower().replace('-', '_') in {'password','api_key','access_token','secret','authorization','cookie','set_cookie','private_key','github_app_private_key','e2b_api_key','ai_api_key','refresh_token','client_secret'} else redact(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    if isinstance(value,str):
        for p in PATTERNS:value=p.sub('[REDACTED]',value)
    return value

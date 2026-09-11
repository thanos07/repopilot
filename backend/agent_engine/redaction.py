import re

PATTERNS=[re.compile(r'\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,})\b'),re.compile(r'(?i)(authorization\s*[:=]\s*["\x27]?bearer\s+)[^\s"\x27]+')]
def redact(value):
    if isinstance(value,dict):return {k:('[REDACTED]' if k.lower() in {'password','api_key','access_token','secret'} else redact(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    if isinstance(value,str):
        for p in PATTERNS:value=p.sub('[REDACTED]',value)
    return value

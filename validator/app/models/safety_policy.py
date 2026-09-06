from pydantic import BaseModel, Field
from typing import List
import json
from pathlib import Path


class SafetyPolicy(BaseModel):
    max_vus: int = Field(default=1000, description="Maximum VUs allowed to prevent resource exhaustion")
    max_duration_seconds: int = Field(default=1800, description="Maximum test duration in seconds (30 minutes)")
    max_stages: int = Field(default=20, description="Maximum number of ramp stages permitted")
    min_vus: int = Field(default=1, description="Minimum virtual users")
    min_duration_seconds: int = Field(default=1, description="Minimum test duration in seconds")
    allow_localhost: bool = Field(default=True, description="Whether localhost/127.0.0.1 is permitted for dev/test")
    allowed_targets: List[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://127.0.0.1",
            "https://example.com",
            "http://test-api",
            "https://staging.internal.net",
            "https://httpbin.org",
            "http://httpbin.org"
        ],
        description="Allowlist of target base URLs or domains"
    )
    blocked_cidrs: List[str] = Field(
        default_factory=lambda: [
            "169.254.169.254/32",  # Cloud metadata endpoint
            "224.0.0.0/4",          # Multicast
            "240.0.0.0/4",          # Reserved
            "255.255.255.255/32"    # Broadcast
        ],
        description="Forbidden CIDRs to block SSRF attacks"
    )

    @classmethod
    def load_from_file(cls, path: str | Path) -> "SafetyPolicy":
        p = Path(path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        return cls()

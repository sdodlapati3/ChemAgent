"""
ChemAgent Configuration Management
Handles environment variables and application configuration.
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ChemAgentConfig:
    """Central configuration for ChemAgent application."""
    
    # Server Configuration
    port: int = 8000
    host: str = "0.0.0.0"
    workers: int = 4
    reload: bool = False
    
    # Parallel Execution
    enable_parallel: bool = True
    max_workers: int = 4
    
    # Caching
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour default
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "chemagent")
    
    # Logging
    log_level: str = "INFO"
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    
    # Security
    enable_auth: bool = False
    api_keys: list[str] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    
    # External APIs
    chembl_base_url: str = "https://www.ebi.ac.uk/chembl/api/data"
    uniprot_base_url: str = "https://rest.uniprot.org"
    request_timeout: int = 30
    
    # Features
    enable_streaming: bool = True
    enable_metrics: bool = True
    
    @classmethod
    def from_env(cls) -> "ChemAgentConfig":
        """Load configuration from environment variables."""
        return cls(
            # Server
            port=int(os.getenv("CHEMAGENT_PORT", "8000")),
            host=os.getenv("CHEMAGENT_HOST", "0.0.0.0"),
            workers=int(os.getenv("CHEMAGENT_WORKERS", "4")),
            reload=os.getenv("CHEMAGENT_RELOAD", "false").lower() == "true",
            
            # Parallel execution
            enable_parallel=os.getenv("CHEMAGENT_PARALLEL", "true").lower() == "true",
            max_workers=int(os.getenv("CHEMAGENT_MAX_WORKERS", "4")),
            
            # Caching
            cache_enabled=os.getenv("CHEMAGENT_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("CHEMAGENT_CACHE_TTL", "3600")),
            cache_dir=Path(os.getenv("CHEMAGENT_CACHE_DIR", str(Path.home() / ".cache" / "chemagent"))),
            
            # Logging
            log_level=os.getenv("CHEMAGENT_LOG_LEVEL", "INFO").upper(),
            log_dir=Path(os.getenv("CHEMAGENT_LOG_DIR", "logs")),
            
            # Security
            enable_auth=os.getenv("ENABLE_AUTH", "false").lower() == "true",
            api_keys=os.getenv("CHEMAGENT_API_KEYS", "").split(",") if os.getenv("CHEMAGENT_API_KEYS") else [],
            rate_limit_per_minute=int(os.getenv("CHEMAGENT_RATE_LIMIT", "60")),
            
            # External APIs
            chembl_base_url=os.getenv("CHEMBL_BASE_URL", "https://www.ebi.ac.uk/chembl/api/data"),
            uniprot_base_url=os.getenv("UNIPROT_BASE_URL", "https://rest.uniprot.org"),
            request_timeout=int(os.getenv("CHEMAGENT_REQUEST_TIMEOUT", "30")),
            
            # Features
            enable_streaming=os.getenv("CHEMAGENT_STREAMING", "true").lower() == "true",
            enable_metrics=os.getenv("CHEMAGENT_METRICS", "true").lower() == "true",
        )
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.port < 1 or self.port > 65535:
            errors.append(f"Invalid port: {self.port} (must be 1-65535)")
        
        if self.workers < 1 or self.workers > 32:
            errors.append(f"Invalid workers: {self.workers} (must be 1-32)")
        
        if self.max_workers < 1 or self.max_workers > 16:
            errors.append(f"Invalid max_workers: {self.max_workers} (must be 1-16)")
        
        if self.cache_ttl < 0:
            errors.append(f"Invalid cache_ttl: {self.cache_ttl} (must be >= 0)")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(f"Invalid log_level: {self.log_level}")
        
        if self.rate_limit_per_minute < 1:
            errors.append(f"Invalid rate_limit: {self.rate_limit_per_minute}")
        
        return errors
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config: Optional[ChemAgentConfig] = None


def get_config() -> ChemAgentConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ChemAgentConfig.from_env()
        _config.ensure_directories()
        
        # Validate configuration
        errors = _config.validate()
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return _config


def load_dotenv_if_exists():
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            return True
    except ImportError:
        pass
    return False

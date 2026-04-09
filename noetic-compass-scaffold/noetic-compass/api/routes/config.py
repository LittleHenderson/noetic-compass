"""GET/PUT /config — dial configuration management."""

from fastapi import APIRouter

try:
    import cas_engine
except ImportError:
    cas_engine = None  # type: ignore[assignment]

from api.errors import DialViolationError
from api.models import DialConfigSchema

router = APIRouter()

# In-memory current config (would be persisted in production)
_current_config = DialConfigSchema()


@router.get("/config", response_model=DialConfigSchema)
async def get_config() -> DialConfigSchema:
    """Get the current dial configuration."""
    return _current_config


@router.put("/config", response_model=DialConfigSchema)
async def put_config(config: DialConfigSchema) -> DialConfigSchema:
    """Update the dial configuration. Returns 422 on constraint violation."""
    global _current_config
    # Validate through Rust engine too
    try:
        cas_engine.DialConfig(config.values)
    except ValueError as e:
        raise DialViolationError(str(e))
    _current_config = config
    return _current_config

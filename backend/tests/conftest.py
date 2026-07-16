from typing import AsyncGenerator
import pytest
from evidencesplit.database import engine


@pytest.fixture(autouse=True)
async def cleanup_database_connections() -> AsyncGenerator[None, None]:
    yield
    # Dispose the engine to clear connection pools bound to the current event loop
    await engine.dispose()

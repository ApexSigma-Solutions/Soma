"""Simple test to see actual error"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from omega_kg.workers.event_processor import EventProcessor
from omega_kg.models.webhook import RawWebhookEvent


async def test():
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    # Mock transaction context manager returned by session.begin()
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=None)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    # Replace begin() method with non-async MagicMock (not as coroutine)
    type(mock_session).begin = MagicMock(return_value=mock_transaction)

    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.id = 123
    mock_event.source = "linear"
    mock_event.payload = {"type": "Issue", "action": "create"}
    mock_event.processed_status = False
    mock_event.error_log = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute.return_value = mock_result

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch(
            "omega_kg.workers.event_processor.get_linear_processor"
        ) as mock_get_lp:
            mock_lp = MagicMock()
            mock_lp.process_single_event.return_value = True
            mock_get_lp.return_value = mock_lp

            processor = EventProcessor()
            count = await processor.process_batch()
            print(f"Count: {count}")


if __name__ == "__main__":
    asyncio.run(test())

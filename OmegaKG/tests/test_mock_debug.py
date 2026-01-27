"""Debug script to test mock setup"""

import asyncio
from unittest.mock import AsyncMock


async def test_mock_setup():
    # Simulate the test setup
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session

    # Mock transaction context manager returned by session.begin()
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=None)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin.return_value = mock_transaction

    print(f"mock_session type: {type(mock_session)}")
    print(f"mock_session.begin type: {type(mock_session.begin)}")
    print(f"mock_session.begin() type: {type(mock_session.begin())}")
    print(f"mock_transaction type: {type(mock_transaction)}")
    print(f"mock_transaction.__aenter__ type: {type(mock_transaction.__aenter__)}")

    # Try using it like the code does
    try:
        async with mock_session as session:
            print("Entered session context")
            async with session.begin():
                print("Entered transaction context")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_mock_setup())

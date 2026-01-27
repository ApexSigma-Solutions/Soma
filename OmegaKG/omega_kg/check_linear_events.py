#!/usr/bin/env python
"""Check Linear webhook events in database"""

import asyncio
from sqlalchemy import select, desc
from omega_kg.models import RawLinearEvent
from omega_kg.database.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RawLinearEvent).order_by(desc(RawLinearEvent.id)).limit(5)
        )
        events = result.scalars().all()

        print(f"Total unprocessed events: {len(events)}")
        print("=" * 70)

        for e in events:
            print(f"\nEvent {e.id}:")
            print(f"  Processed: {e.processed}")
            print(f"  Action: {e.action}")
            print(f"  Event Type: {e.event_type}")

            body = e.body
            if body and "data" in body:
                data = body.get("data", {})
                print(f"  Issue ID: {data.get('id', 'N/A')}")
                print(f"  Identifier: {data.get('identifier', 'N/A')}")
                print(f"  Title: {data.get('title', 'N/A')[:50]}...")

            if e.error_log:
                print(f"  Error: {e.error_log[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())

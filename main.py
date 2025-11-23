"""
Entry point для запуска бота.
Простая обёртка, которая запускает основное приложение из пакета app.
"""

import asyncio
from app.bot import main

if __name__ == "__main__":
    asyncio.run(main())


"""Runtime status tests that do not need a database or an AI provider."""

import os
import unittest

from app import dependencies


class RuntimeStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_placeholder_key_keeps_core_runtime_alive_but_disables_ai(self):
        previous = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "local-placeholder"
        try:
            from fastapi import FastAPI

            async with dependencies.lifespan(FastAPI()):
                status = dependencies.get_runtime_status()
                self.assertTrue(status["core_ready"])
                self.assertEqual(status["ai"], {
                    "available": False,
                    "reason": "OpenRouter API key is not configured",
                })
        finally:
            if previous is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()

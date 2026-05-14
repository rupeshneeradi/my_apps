"""Rotating Apify token pool — cycles to next token on quota/rate errors."""
import time
import logging
from apify_client import ApifyClient
from config import APIFY_TOKENS

log = logging.getLogger(__name__)

class ApifyPool:
    def __init__(self):
        if not APIFY_TOKENS:
            raise RuntimeError("No APIFY_TOKEN* set in .env")
        self._tokens = list(APIFY_TOKENS)
        self._idx    = 0
        self._client = ApifyClient(self._tokens[0])

    def _rotate(self):
        self._idx = (self._idx + 1) % len(self._tokens)
        token = self._tokens[self._idx]
        self._client = ApifyClient(token)
        log.warning("Rotated to Apify token #%d", self._idx + 1)

    def run_actor(self, actor_id: str, run_input: dict, timeout_secs: int = 300) -> list:
        """Run an Apify actor and return dataset items. Rotates token on quota error."""
        last_exc = None
        for attempt in range(len(self._tokens)):
            try:
                log.info("Running actor %s (token #%d)", actor_id, self._idx + 1)
                run = self._client.actor(actor_id).call(
                    run_input=run_input,
                    timeout_secs=timeout_secs,
                    memory_mbytes=256,
                )
                items = list(
                    self._client.dataset(run["defaultDatasetId"]).iterate_items()
                )
                log.info("  → %d items from %s", len(items), actor_id)
                return items
            except Exception as exc:
                msg = str(exc).lower()
                if any(k in msg for k in ("quota", "limit", "rate", "429", "402")):
                    log.warning("Quota/rate error on token #%d: %s", self._idx + 1, exc)
                    last_exc = exc
                    self._rotate()
                    time.sleep(5)
                else:
                    log.error("Actor %s failed: %s", actor_id, exc)
                    raise
        raise RuntimeError(f"All Apify tokens exhausted. Last error: {last_exc}")

# Singleton — import and reuse across the pipeline
pool = ApifyPool()

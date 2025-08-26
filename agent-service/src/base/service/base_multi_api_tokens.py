import logging
import time

from pydantic import BaseModel, Field

from src.enums.enums import ModelTypeEnum
from src.settings import GOOGLE_API_KEYS, get_redis_client

redis_round_robin_key = "round_robin_{model_type}"
redis_round_robin_lock_key = "round_robin_{model_type}_lock"
LOCK_TIMEOUT = 5


class BaseMultiApiTokens(BaseModel):
    model_type: ModelTypeEnum = Field(
        default=ModelTypeEnum.llm.value,
        description="Type of model (llm or embedding)",
    )

    def _reset_round_robin(self):
        redis_client = get_redis_client()
        model_key = redis_round_robin_key.format(model_type=self.model_type)
        lock_key = redis_round_robin_lock_key.format(model_type=self.model_type)

        got_lock = redis_client.set(lock_key, "1", nx=True, ex=LOCK_TIMEOUT)

        if got_lock:
            try:
                logging.info(f"Resetting round robin for model type: {self.model_type}")
                if not GOOGLE_API_KEYS:
                    raise ValueError("GOOGLE_API_KEYS is empty.")

                model_index = list(range(len(GOOGLE_API_KEYS)))

                redis_client.delete(model_key)  # Xóa trước khi push
                redis_client.rpush(model_key, *model_index)
            finally:
                redis_client.delete(lock_key)
        else:
            time.sleep(0.1)

    def _get_next_model_index(self):
        model_key = redis_round_robin_key.format(model_type=self.model_type)
        while True:
            if get_redis_client().llen(model_key) == 0:
                self._reset_round_robin()

            idx = get_redis_client().lpop(model_key)
            if idx is not None:
                return int(idx)
            time.sleep(0.1)

from abc import ABC, abstractmethod
from typing import Any


class AIService(ABC):

    @abstractmethod
    def process(
        self,
        *,
        page_id: int,
        input_data: Any,
    ) -> dict:
        raise NotImplementedError
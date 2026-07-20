from typing import Self


class FakeUnitOfWork:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ):
        if exc_type is not None:
            self.rolled_back = True
            return
        self.committed = True

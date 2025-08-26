import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_application_registry():
    """
    Fixture này tự động chạy MỘT LẦN DUY NHẤT khi phiên test bắt đầu.
    Nó gọi hàm quét để điền vào NODE_REGISTRY.
    """
    pass

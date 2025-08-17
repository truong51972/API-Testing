from dotenv import load_dotenv

from src.graph.nodes.docs_preprocessing.metadata_removal import MetaDataRemoval


def test_metadata_removal_vn():
    load_dotenv()
    meta_data_removal = MetaDataRemoval()

    string = """
    Tác giả: Nguyễn Văn A
    Ngày tạo: 15/08/2025
    Email: nguyenvana@example.com
    Số điện thoại: 0912 345 678
    Nhóm: Nghiên cứu AI

    Báo cáo kết quả tuần
    Tuần này, nhóm đã hoàn thành việc kiểm thử hệ thống AI cho dự án mới.
    Các vấn đề phát sinh đã được ghi nhận và xử lý kịp thời.
    Kế hoạch tuần tới là tối ưu hóa thuật toán và cập nhật tài liệu hướng dẫn sử dụng.
    """
    state = type("State", (object,), {"data": string, "lang": "vi"})()

    response = meta_data_removal(state)["result"][0]

    assert "15/08/2025" not in response
    assert "Nguyễn Văn A" not in response
    assert "nguyenvana@example.com" not in response
    assert "0912 345 678" not in response
    assert "Nghiên cứu AI" not in response


def test_metadata_removal_en():
    load_dotenv()
    meta_data_removal = MetaDataRemoval()

    string = """
    Author: John Doe
    Created on: 15/08/2025
    Email: johndoe@example.com
    Phone: 0912 345 678
    Group: AI Research

    Weekly Report
    This week, the group completed testing the AI system for the new project.
    Issues that arose were recorded and addressed in a timely manner.
    The plan for next week is to optimize the algorithm and update the user manual.
    """
    state = type("State", (object,), {"data": string, "lang": "en"})()

    response = meta_data_removal(state)["result"][0]

    assert "15/08/2025" not in response
    assert "John Doe" not in response
    assert "johndoe@example.com" not in response
    assert "0912 345 678" not in response
    assert "AI Research" not in response

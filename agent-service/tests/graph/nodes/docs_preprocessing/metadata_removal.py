from langchain_core.messages import HumanMessage

from src.graph import nodes
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel


def test_metadata_removal_vn():
    data_test = """
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
    node = nodes.MetaDataRemovalNode()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content

    assert "15/08/2025" not in result
    assert "Nguyễn Văn A" not in result
    assert "nguyenvana@example.com" not in result
    assert "0912 345 678" not in result
    assert "Nghiên cứu AI" not in result


def test_metadata_removal_en():
    data_test = """
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
    node = nodes.MetaDataRemovalNode()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="en")

    result = node(state)["messages"][-1].content

    assert "15/08/2025" not in result
    assert "John Doe" not in result
    assert "johndoe@example.com" not in result
    assert "0912 345 678" not in result
    assert "AI Research" not in result

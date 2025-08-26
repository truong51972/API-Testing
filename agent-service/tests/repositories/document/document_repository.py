from src.repositories.document.document_repository import DocumentRepository
from random import randint
from time import sleep


def test_document_repository():
    doc_repo = DocumentRepository(collection_name="unit_test")

    random_id = randint(1, 1000000)
    data = [
        {
            "id": random_id,
            "doc_name": "he he",
            "annotations": "he he he",
            "text": "hehehehe",
        }
    ]

    doc_repo.create_records(data)
    sleep(1)
    records = doc_repo.read_records([random_id])

    assert records[0]["doc_name"] == "he he"
    assert records[0]["annotations"] == "he he he"
    assert records[0]["text"] == "hehehehe"

    data = [
        {
            "id": random_id,
            "doc_name": "HE HE",
            "annotations": "HE HE HE",
            "text": "HEHEHEHE",
        }
    ]

    doc_repo.update_records(data)
    sleep(1)

    records = doc_repo.read_records([random_id])
    assert records[0]["doc_name"] == "HE HE"
    assert records[0]["annotations"] == "HE HE HE"
    assert records[0]["text"] == "HEHEHEHE"


if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:[%(levelname)-4s] [%(module)s] [%(funcName)s]: %(message)s",
    )

    test_document_repository()
    print("Document repository tests passed successfully!")

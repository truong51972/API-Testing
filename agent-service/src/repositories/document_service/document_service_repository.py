# src.repositories.document_service.document_service_repository
from datetime import timedelta
from src.settings import get_minio_client


if __name__ == "__main__":
    # Example usage of the MinIO client
    minio_client = get_minio_client()
    print("MinIO client initialized successfully.")
    # You can now use minio_client to interact with your MinIO server

    bucket_name = "mybucket"
    found = minio_client.bucket_exists(bucket_name)
    if not found:
        minio_client.make_bucket(bucket_name)
    else:
        print("Bucket đã tồn tại")

    minio_client.fput_object(
        bucket_name,  # Tên bucket
        "mac-lenin.pdf",  # Tên file trên MinIO
        "data/uploads/mac-lenin.pdf",  # Đường dẫn file local
    )
    print("Upload thành công!")

    url = minio_client.presigned_get_object(
        bucket_name, "mac-lenin.pdf", expires=timedelta(hours=1)
    )
    print("URL truy cập file:", url)

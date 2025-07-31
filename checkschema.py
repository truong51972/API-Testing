import json
from os import name

from jsonschema import SchemaError, ValidationError, validate

# Ví dụ JSON Schema
schema = {
    "type": "object",
    "properties": {
        "username": {"type": "string"},
        "age": {"type": "integer", "minimum": 0, "maximum": 120},
        "email": {"type": "string", "format": "email"},
        "gender": {"type": "string", "enum": ["male", "female", "other"]},
    },
    "required": ["username", "email", "gender"],
}

# Ví dụ dữ liệu JSON để kiểm tra
data = {
    "username": "truong51972",
    "age": 121,
    "email": "truong51972@example.com",
    "gender": "male1",
}

try:
    validate(instance=data, schema=schema)
    print("JSON hợp lệ với schema!")
except ValidationError as ve:
    print("JSON không hợp lệ:", ve.message)
except SchemaError as se:
    print("Schema không hợp lệ:", se)

# src.services.test_case.execute_test_case
import random
import re
import string

import requests
from sqlmodel import Session

from src import repositories
from src.settings import get_db_engine, get_now_vn


def replace_value(value):
    """
    Replace special value patterns with actual values using regex.
    """
    if value == "N/A":
        return ""
    if value == "NULL":
        return None
    if isinstance(value, str):
        # CHARS(n)
        match = re.fullmatch(r"CHARS\((\d+)\)", value)
        if match:
            n = int(match.group(1))
            return "".join(random.choices(string.ascii_letters, k=n))
        # NUMS(n)
        match = re.fullmatch(r"NUMS\((\d+)\)", value)
        if match:
            n = int(match.group(1))
            return "".join(random.choices(string.digits, k=n))
        # ALPHANUMS(n)
        match = re.fullmatch(r"ALPHANUMS\((\d+)\)", value)
        if match:
            n = int(match.group(1))
            chars = string.ascii_letters + string.digits
            return "".join(random.choices(chars, k=n))
        # EMAIL(n)
        match = re.fullmatch(r"EMAIL\((\d+)\)", value)
        if match:
            n = int(match.group(1))
            local_len = max(1, n - 10)
            local = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=local_len)
            )
            domain = "".join(random.choices(string.ascii_lowercase, k=5))
            return f"{local}@{domain}.com"
    return value


def clean_request_body(request_body):
    """
    Remove fields with value 'ABSENT' and replace special values.
    Support nested dicts and lists.
    """
    if isinstance(request_body, dict):
        cleaned = {}
        for k, v in request_body.items():
            if v == "ABSENT":
                continue
            elif isinstance(v, (dict, list)):
                cleaned[k] = clean_request_body(v)
            else:
                cleaned[k] = replace_value(v)
        return cleaned
    elif isinstance(request_body, list):
        return [
            (
                clean_request_body(item)
                if isinstance(item, (dict, list))
                else replace_value(item)
            )
            for item in request_body
            if item != "ABSENT"
        ]
    else:
        return replace_value(request_body)


def execute_test_case(
    test_case: repositories.TestCaseRepository,
    test_suite_id: str,
) -> repositories.TestCaseReportRepository:
    url = test_case.api_info.get("url")

    method = test_case.api_info.get("method", "GET").upper()
    headers = test_case.api_info.get("headers", {})
    request_body = clean_request_body(test_case.request_body)
    expected_output = test_case.expected_output

    expected_status_code = str(expected_output.get("statuscode"))
    expected_response_mapping = expected_output.get("response_mapping", {})

    try:
        start_time = get_now_vn()
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=request_body)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=request_body)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, json=request_body)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=request_body)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        ended_time = get_now_vn()
        try:
            json_response = response.json()
        except Exception:
            json_response = {}

        execution_result = repositories.TestCaseReportRepository(
            test_suite_report_id=test_suite_id,  # This should be set appropriately
            test_case_id=test_case.id,
            request_header=headers,
            request_body=request_body,
            response_header=dict(response.headers),
            response_body=json_response if response.content else {},
            response_status_code=response.status_code,
            status=(
                "passed"
                if str(response.status_code) == expected_status_code
                else "failed"
            ),
            start_time=start_time,
            end_time=ended_time,
        )

    except Exception as e:
        execution_result = repositories.TestCaseReportRepository(
            test_suite_report_id=test_suite_id,
            test_case_id=test_case.id,
            status=f"error: {str(e)}",
            start_time=get_now_vn(),
            end_time=get_now_vn(),
            request_body=clean_request_body(test_case.request_body),
            request_header=test_case.api_info.get("headers", {}),
            response_body={},
            response_header={},
            response_status_code=0,
        )
    return execution_result


def execute_test_suite(test_suite_report_id: str, test_suite_id: str) -> dict:
    test_suite_report = repositories.TestSuiteReportRepository(
        id=test_suite_report_id, test_suite_id=test_suite_id
    )
    test_cases = repositories.TestCaseRepository.get_all_by_test_suite_id(
        test_suite_id=test_suite_id, execute=True
    )

    execution_results = []

    for test_case in test_cases:
        result = execute_test_case(
            test_case=test_case, test_suite_id=test_suite_report.id
        )
        execution_results.append(result)
        # break

    with Session(get_db_engine()) as session:
        session.add(test_suite_report)
        session.commit()

        session.add_all(execution_results)
        session.commit()


if __name__ == "__main__":

    execute_test_suite("82939c25-b61d-4478-b986-8de7164b5b45")

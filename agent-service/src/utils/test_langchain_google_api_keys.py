# src.utils.test_langchain_google_api_keys
import os

from dotenv import load_dotenv
from google.api_core import exceptions
from langchain_google_genai import ChatGoogleGenerativeAI


def test_langchain_google_api_keys(api_keys: list[str]) -> dict:
    """
    Check a list of Google AI (Gemini) API keys using
    the ChatGoogleGenerativeAI class from LangChain.

    Args:
        api_keys: A list containing API key strings to check.

    Returns:
        A dictionary with two keys:
        - 'valid_keys': list of active keys.
        - 'invalid_keys': dictionary with key as the invalid key and value as the error reason.
    """
    valid_keys = []
    invalid_keys = {}

    print(f"Starting to check {len(api_keys)} API keys with LangChain...")

    for i, key in enumerate(api_keys):
        key_display = f"...{key[-4:]}" if len(key) > 4 else key
        print(f"[{i+1}/{len(api_keys)}] Checking key '{key_display}'")

        if not key or not isinstance(key, str) or len(key.strip()) == 0:
            print("    -> Error: Key is empty or invalid, skipping.")
            # Use index to avoid empty key as dict key
            invalid_keys[f"empty_or_invalid_key_{i+1}"] = (
                "Key is empty, None, or invalid."
            )
            continue

        try:
            # 1. Initialize LangChain LLM object with current key
            # Use a popular model and temperature = 0 for consistent results
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash", google_api_key=key, temperature=0
            )

            # 2. Make a lightweight API call to check
            # The invoke() method sends a request to Google's server
            llm.invoke("Say hi")

            # 3. If no error, this key is valid
            valid_keys.append(key)
            print("    -> ✅ Success: Key is valid.")

        except (exceptions.PermissionDenied, exceptions.Unauthenticated) as e:
            # Authentication error (403, 401): Key is wrong, revoked, or project not enabled
            error_message = str(e)
            # Shorten error message for readability
            if "API key not valid" in error_message:
                reason = "Authentication error: API key is invalid."
            else:
                reason = f"Authentication error (Permission Denied/Unauthenticated): {error_message}"
            invalid_keys[key] = reason
            print(f"    -> ❌ Error: {reason}")

        except exceptions.ResourceExhausted as e:
            # Error 429: Key may be valid but has reached rate limit
            invalid_keys[key] = f"Rate limit exceeded: {e}"
            print("    -> ⚠️ Error: Rate limit exceeded.")

        except Exception as e:
            # Catch other errors (e.g., network, server, malformed key)
            invalid_keys[key] = f"Unknown error: {type(e).__name__} - {e}"
            print("    -> ❌ Error: An unknown issue occurred.")

    print("\nCheck completed!")
    return {"valid_keys": valid_keys, "invalid_keys": invalid_keys}


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    from src.settings import GOOGLE_API_KEYS

    # Load environment variables from .env file
    load_dotenv()

    # Read list of keys from environment variable
    # Assume your .env file contains:
    # GOOGLE_API_KEYS='key_real_123,key_fake_abc,key_real_456'
    list_of_keys_to_test = GOOGLE_API_KEYS

    # If no environment variable, use demo list
    if not list_of_keys_to_test:
        print("GOOGLE_API_KEYS environment variable not found, using demo list.")
        list_of_keys_to_test = [
            os.getenv("GOOGLE_API_KEY"),  # Try to get a real key if available
            "AIzaSyA_this_is_a_completely_fake_key_12345",  # Fake key
            "another-invalid-key-format-that-will-fail",  # Malformed key
            "",  # Empty key
        ]

    # Filter out empty or None keys
    list_of_keys_to_test = [key for key in list_of_keys_to_test if key]

    results = test_langchain_google_api_keys(list_of_keys_to_test)

    print("\n" + "=" * 30)
    print("--- SUMMARY RESULT ---")
    print("=" * 30)

    print(f"\n✅ Number of valid keys: {len(results['valid_keys'])}")
    if results["valid_keys"]:
        for key in results["valid_keys"]:
            print(f"  - Key ends with: ...{key[-4:]}")

    print(f"\n❌ Number of invalid keys: {len(results['invalid_keys'])}")
    if results["invalid_keys"]:
        for key, reason in results["invalid_keys"].items():
            key_display = f"...{key[-4:]}" if len(key) > 4 else key
            print(f"\n  - Key: {key_display}\n    Reason: {reason}")

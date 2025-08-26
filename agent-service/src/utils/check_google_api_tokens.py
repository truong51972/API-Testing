# src.utils.test_langchain_google_api_keys
import logging
from typing import Optional

from google.api_core import exceptions
from langchain_google_genai import GoogleGenerativeAI


def check_google_api_tokens(tokens: Optional[list[str]] = None):
    for i, key in enumerate(tokens):
        key_display = f"...{key[-4:]}" if len(key) > 4 else key

        logging.info(f"[{i+1}/{len(tokens)}] Checking key '{key_display}'")
        if not key or not isinstance(key, str) or len(key.strip()) == 0:
            assert False, "Key is empty, None, or invalid."
        try:
            model = GoogleGenerativeAI(
                model="gemma-3n-e4b-it", google_api_key=key, temperature=0
            )

            model.invoke("Say hi")

            logging.info("API key is valid.")

        except (exceptions.PermissionDenied, exceptions.Unauthenticated) as e:
            # Authentication error (403, 401): Key is wrong, revoked, or project not enabled
            error_message = str(e)
            # Shorten error message for readability
            if "API key not valid" in error_message:
                reason = "Authentication error: API key is invalid."
            else:
                reason = f"Authentication error (Permission Denied/Unauthenticated): {error_message}"

            logging.error(f"API key is invalid: {reason}")
            raise ValueError(f"API key is invalid: {reason}")

        except exceptions.ResourceExhausted as e:
            # Error 429: Key may be valid but has reached rate limit
            logging.warning(f"API key has reached rate limit: {e}")

        except Exception as e:
            reason = str(e)
            # Catch other errors (e.g., network, server, malformed key)
            logging.error(f"An unknown issue occurred: {e}")
            raise ValueError(f"API key is invalid: {reason}")

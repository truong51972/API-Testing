# src.utils.text_preprocessing
import re
import string
import unicodedata


def remove_stopwords(text, stopwords):
    lines = text.splitlines()
    result = []
    for line in lines:
        words = line.split()
        result.append(" ".join([w for w in words if w not in stopwords]))
    return "\n".join(result)


def remove_punctuation(text):
    return text.translate(str.maketrans("", "", string.punctuation))


def remove_repeated_punctuation(text, ignore_code_blocks=False):
    """
    Remove repeated punctuation from text while optionally preserving code blocks.

    Args:
        text (str): Input text to clean
        ignore_code_blocks (bool): If True, preserve formatting inside code blocks

    Returns:
        str: Text with repeated punctuation removed
    """

    def _remove_repeated_punctuation(text):
        # Replace multiple consecutive punctuation with single occurrence
        pattern = r"([%s])\1+" % re.escape(string.punctuation)
        return re.sub(pattern, r"\1", text)

    # If not preserving code blocks, apply simple punctuation removal
    if not ignore_code_blocks:
        return _remove_repeated_punctuation(text)

    # Pattern to match code blocks (``` or ~~~ delimited)
    code_block_pattern = re.compile(r"(```.*?```|~~~.*?~~~)", re.DOTALL)
    blocks = []  # Store processed text blocks
    last_idx = 0  # Track position in original text

    # Process each code block found
    for match in code_block_pattern.finditer(text):
        start, end = match.span()

        # Clean repeated punctuation in text before this code block
        if start > last_idx:
            blocks.append(_remove_repeated_punctuation(text[last_idx:start]))

        # Preserve code block as-is (no punctuation cleaning)
        blocks.append(text[start:end])
        last_idx = end

    # Clean remaining text after last code block
    if last_idx < len(text):
        blocks.append(_remove_repeated_punctuation(text[last_idx:]))

    # Join all blocks back together
    return "".join(blocks)


def remove_extra_whitespace(text, ignore_code_blocks=False):
    """
    Remove extra whitespace from text while optionally preserving code blocks.

    Args:
        text (str): Input text to clean
        ignore_code_blocks (bool): If True, preserve formatting inside code blocks

    Returns:
        str: Text with extra whitespace removed
    """

    def _remove_extra_whitespace(text):
        # Replace multiple consecutive whitespace characters with single space
        # and strip leading/trailing whitespace
        return "\n".join(
            re.sub(r"[ ]+", " ", line.strip()) for line in text.splitlines()
        )

    # If not preserving code blocks, apply simple whitespace removal
    if not ignore_code_blocks:
        return _remove_extra_whitespace(text)

    # Pattern to match code blocks (``` or ~~~ delimited)
    code_block_pattern = re.compile(r"(```.*?```|~~~.*?~~~)", re.DOTALL)
    blocks = []  # Store processed text blocks
    last_idx = 0  # Track position in original text

    # Process each code block found
    for match in code_block_pattern.finditer(text):
        start, end = match.span()

        # Clean whitespace in text before this code block
        if start > last_idx:
            blocks.append(_remove_extra_whitespace(text[last_idx:start]))

        # Preserve code block as-is (no whitespace cleaning)
        blocks.append(text[start:end])
        last_idx = end

    # Clean remaining text after last code block
    if last_idx < len(text):
        blocks.append(_remove_extra_whitespace(text[last_idx:]))

    # Join all blocks back together
    return "\n".join(block for block in blocks if block.strip() != "")


def normalize_unicode(text):
    return unicodedata.normalize("NFKC", text)


def lowercase_text(text):
    return text.lower()


def extract_link_text(text):
    pattern = r"\[([^\]]+)\]\([^\)]+\)"
    return re.sub(pattern, r"\1", text)


if __name__ == "__main__":
    # initialize_nltk()

    with open("src/resources/vietnamese-stopwords.txt", "r", encoding="utf-8") as f:
        vn_stopwords = f.read().splitlines()

    original_text = "Tôi là một học sinh ở trường trung học. Mỗi ngày, tôi đều đi học cùng bạn bè và thầy cô. Ở lớp, chúng tôi thường học các môn như toán, văn, và tiếng Anh. Sau giờ học, tôi về nhà ăn cơm với gia đình rồi làm bài tập. Tôi rất thích đọc sách vào buổi tối trước khi đi ngủ."

    cleaned_text = remove_stopwords(lowercase_text(original_text), vn_stopwords)

    print(cleaned_text)

# tests.utils.text_preprocessing
from src.utils.preprocessing.text_preprocessing import (
    extract_link_text,
    lowercase_text,
    normalize_unicode,
    remove_extra_newlines,
    remove_extra_whitespace,
    remove_punctuation,
    remove_repeated_punctuation,
    remove_stopwords,
)


def test_remove_extra_whitespace():
    assert remove_extra_whitespace("  Hello   World!  ") == "Hello World!"
    assert remove_extra_whitespace("  This   is a test.  ") == "This is a test."
    assert remove_extra_whitespace("NoExtraSpaces") == "NoExtraSpaces"
    assert (
        remove_extra_whitespace("  Leading and trailing spaces   ")
        == "Leading and trailing spaces"
    )
    assert remove_extra_whitespace("") == ""

    test_data = (
        "this  is         a block  code \n\n"
        "```\n"
        '   print("Hello, World!")\n'
        "```\n"
        "~~~\n"
        '   print("Hello, World!")\n'
        "~~~\n"
    )

    expected = (
        "this is a block code\n\n"
        "```\n"
        '   print("Hello, World!")\n'
        "```\n"
        "~~~\n"
        '   print("Hello, World!")\n'
        "~~~"
    )

    assert remove_extra_whitespace(test_data, True) == expected


def test_remove_punctuation():
    assert remove_punctuation("Hello, World!") == "Hello World"
    assert remove_punctuation("This is a test.") == "This is a test"
    assert remove_punctuation("NoPunctuation") == "NoPunctuation"
    assert (
        remove_punctuation("  Leading and trailing punctuation...   ")
        == "  Leading and trailing punctuation   "
    )


def test_remove_stopwords():
    stopwords = {"is", "a", "the"}
    assert remove_stopwords("This is a test.", stopwords) == "This test."
    assert remove_stopwords("No stopwords here.", stopwords) == "No stopwords here."
    assert remove_stopwords("the quick brown fox.", stopwords) == "quick brown fox."


def test_normalize_unicode():
    assert normalize_unicode("Hello, World!") == "Hello, World!"
    assert normalize_unicode("This is a test.") == "This is a test."
    assert normalize_unicode("NoPunctuation") == "NoPunctuation"
    assert (
        normalize_unicode("  Leading and trailing whitespace...   ")
        == "  Leading and trailing whitespace...   "
    )


def test_lowercase_text():
    assert lowercase_text("Hello, World!") == "hello, world!"
    assert lowercase_text("This is a test.") == "this is a test."
    assert lowercase_text("NoPunctuation") == "nopunctuation"
    assert (
        lowercase_text("  Leading and trailing whitespace...   ")
        == "  leading and trailing whitespace...   "
    )


def test_remove_repeated_punctuation():
    assert remove_repeated_punctuation("Hello!!!") == "Hello!"
    assert remove_repeated_punctuation("What??") == "What?"
    assert remove_repeated_punctuation("This is a test...") == "This is a test."
    assert (
        remove_repeated_punctuation("Single. Punctuation! Stays?")
        == "Single. Punctuation! Stays?"
    )

    test_data = (
        "this is a block code!!!!!!!!!!!!\n\n"
        "```\n"
        '   print("Hello, World!!")\n'
        "```\n"
        "~~~\n"
        '   print("Hello, World!")\n'
        "~~~"
    )

    expected = (
        "this is a block code!\n\n"
        "```\n"
        '   print("Hello, World!!")\n'
        "```\n"
        "~~~\n"
        '   print("Hello, World!")\n'
        "~~~"
    )

    assert remove_repeated_punctuation(test_data, True) == expected


def test_extract_link_text():
    assert extract_link_text("[link text](url)") == "link text"
    assert extract_link_text("No links here.") == "No links here."
    assert extract_link_text("[another link](http://example.com)") == "another link"


def test_remove_extra_newlines():
    assert remove_extra_newlines("Hello\n\n\nWorld") == "Hello\nWorld"
    assert remove_extra_newlines("This\n\n\n\n\nis a test") == "This\nis a test"
    assert remove_extra_newlines("Single\nNewline") == "Single\nNewline"
    assert remove_extra_newlines("Double\n\nNewline") == "Double\nNewline"
    assert remove_extra_newlines("") == ""
    assert remove_extra_newlines("No newlines") == "No newlines"

    test_data = (
        "This has many\n\n\n\nnewlines\n\n\n"
        "```\n"
        "code block with\n\n\n\nmany newlines\n"
        "```\n\n\n\n"
        "~~~\n"
        "another code\n\n\n\nblock\n"
        "~~~\n\n\n\nEnd"
    )

    expected = (
        "This has many\nnewlines\n"
        "```\n"
        "code block with\n\n\n\nmany newlines\n"
        "```\n"
        "~~~\n"
        "another code\n\n\n\nblock\n"
        "~~~\nEnd"
    )

    assert remove_extra_newlines(test_data, True) == expected


if __name__ == "__main__":
    test_remove_extra_whitespace()

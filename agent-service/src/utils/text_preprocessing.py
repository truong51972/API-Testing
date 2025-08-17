# src.utils.text_preprocessing
import re
import string
import unicodedata


def remove_stopwords(text, stopwords):
    words = text.split()
    return " ".join([w for w in words if w not in stopwords])


def remove_punctuation(text):
    return text.translate(str.maketrans("", "", string.punctuation))


def remove_extra_whitespace(text):
    return re.sub(r"\s+", " ", text.strip())


def normalize_unicode(text):
    return unicodedata.normalize("NFKC", text)


def lowercase_text(text):
    return text.lower()


if __name__ == "__main__":
    # initialize_nltk()

    with open("src/resources/vietnamese-stopwords.txt", "r", encoding="utf-8") as f:
        vn_stopwords = f.read().splitlines()

    original_text = "Tôi là một học sinh ở trường trung học. Mỗi ngày, tôi đều đi học cùng bạn bè và thầy cô. Ở lớp, chúng tôi thường học các môn như toán, văn, và tiếng Anh. Sau giờ học, tôi về nhà ăn cơm với gia đình rồi làm bài tập. Tôi rất thích đọc sách vào buổi tối trước khi đi ngủ."

    cleaned_text = remove_stopwords(lowercase_text(original_text), vn_stopwords)

    print(cleaned_text)

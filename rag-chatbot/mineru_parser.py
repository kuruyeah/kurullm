import json
import re
from pathlib import Path

from transformers import AutoTokenizer


# ============================================================
# CONFIG
# ============================================================

INPUT_JSON = Path(r".\test_mineru\output\structured_content.json")
OUTPUT_JSON = Path(r".\test_mineru\parsed_chunks_v4_2.json")

DOCUMENT_ID = "DOC001"
FILE_ID = "FILE001"
DOCUMENT_TITLE = "Registrasi Akun ULT - Mahasiswa"

CATEGORY_ID = "CAT001"
CATEGORY_NAME = "Peraturan Akademik"

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

CHUNK_SIZE = 350
CHUNK_OVERLAP = 50


# ============================================================
# TOKENIZER
# ============================================================

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
print("Tokenizer loaded.")


# ============================================================
# BASIC CLEANING
# ============================================================

def repair_mojibake(text):
    if not text:
        return text

    suspicious = ("â", "Â", "Ã", "ð")

    if not any(char in text for char in suspicious):
        return text

    try:
        repaired = text.encode("latin1").decode("utf-8")

        before = sum(text.count(x) for x in suspicious)
        after = sum(repaired.count(x) for x in suspicious)

        if after < before:
            return repaired

    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    return text


def clean_text(text):

    if not isinstance(text, str):
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    text = repair_mojibake(text)

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces before punctuation
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)

    # Common OCR spacing
    text = re.sub(
        r"\bNo\.\s+file\b",
        "No file",
        text,
        flags=re.I
    )

    # Common joined words
    text = re.sub(
        r"\bdan juga\b",
        "dan juga",
        text,
        flags=re.I
    )

    # Excessive newline
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# UI / NAVIGATION DETECTION
# ============================================================

MENU_TERMS = [
    "dashboard",
    "profile mahasiswa",
    "pengajuan surat pengantar",
    "pengajuan surat keterangan lulus",
    "pendaftaran bimbingan proposal",
    "pendaftaran sidang proposal",
    "hasil sidang proposal",
    "informasi sidang proposal",
    "logbook mahasiswa",
    "bimbingan akhir",
    "pendaftaran wisuda",
]


def looks_like_navigation_dump(text):

    text = clean_text(text)

    if not text:
        return False

    normalized = text.lower()

    hits = sum(
        1
        for term in MENU_TERMS
        if term in normalized
    )

    # Banyak nama menu sekaligus
    if hits >= 4:

        # Kalau hampir tidak ada kalimat,
        # kemungkinan besar sidebar/navigation.
        sentence_marks = len(
            re.findall(
                r"[.!?]",
                normalized
            )
        )

        if sentence_marks <= 1:
            return True

    return False


def remove_ui_fragments(text):

    if not text:
        return ""

    patterns = [

        # File upload UI
        r"\bNo file chosen\b",
        r"\bChoose file\b",
        r"\bChoose niie\b",

        # Pagination
        r"\bShow\s+\d+\s+per\s+page\b",
        r"\b\d+\s*-\s*\d+\s+of\s+\d+\b",

        # Common standalone actions
        r"\bEdit\s+Delete\s+Kirim\b",
        r"\bDraft\s+Print\b",
    ]

    for pattern in patterns:

        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.I
        )

    return clean_text(text)


# ============================================================
# TABLE CLASSIFICATION
# ============================================================

def table_contains_example_personal_data(text):

    normalized = text.lower()

    indicators = [

        # Personal/example data
        "nama mahasiswa",
        "nim",
        "nama lengkap",

        # Academic record example
        "judul tugas proposal",
        "dosen pembimbing",

        # Example UI table
        "action",
        "show 5 per page",
        "show 10 per page",
    ]

    hits = sum(
        1
        for indicator in indicators
        if indicator in normalized
    )

    return hits >= 2


def table_contains_ui_actions(text):

    normalized = text.lower()

    action_terms = [
        "edit",
        "delete",
        "detail",
        "print",
        "kirim",
        "action",
        "show ",
        "per page",
    ]

    hits = sum(
        1
        for term in action_terms
        if term in normalized
    )

    return hits >= 2


def table_is_example_record(text):

    normalized = text.lower()

    example_indicators = [

        "arrival dwi sentosa",
        "dinda fatimah",
        "zendi ikilima",
        "predictive models for scope",
        "teknik informatika",
    ]

    return any(
        indicator in normalized
        for indicator in example_indicators
    )


# ============================================================
# TABLE PARSER
# ============================================================

def clean_table_cell(cell):

    cell = re.sub(
        r"<[^>]+>",
        " ",
        cell
    )

    cell = clean_text(cell)

    if not cell:
        return ""

    return cell


def html_table_to_text(html):

    if not isinstance(html, str):
        return ""

    rows = re.findall(
        r"<tr[^>]*>(.*?)</tr>",
        html,
        flags=re.I | re.S
    )

    if not rows:
        return ""

    result = []

    for row in rows:

        cells = re.findall(
            r"<t[dh][^>]*>(.*?)</t[dh]>",
            row,
            flags=re.I | re.S
        )

        cleaned = []

        for cell in cells:

            cell = clean_table_cell(cell)

            if cell:
                cleaned.append(cell)

        if not cleaned:
            continue

        row_text = " | ".join(cleaned)

        # Pagination
        if re.search(
            r"show\s+\d+\s+per\s+page",
            row_text,
            flags=re.I
        ):
            continue

        if re.search(
            r"\d+\s*-\s*\d+\s+of\s+\d+",
            row_text,
            flags=re.I
        ):
            continue

        result.append(row_text)

    if not result:
        return ""

    table_text = "\n".join(result)

    # Entire table is just example/UI data
    if table_is_example_record(table_text):
        return ""

    if table_contains_example_personal_data(table_text):
        return ""

    if table_contains_ui_actions(table_text):

        # Try to retain header/procedural information,
        # but remove obvious example rows.

        filtered_rows = []

        for row in result:

            lower = row.lower()

            if any(
                name in lower
                for name in [
                    "arrival dwi sentosa",
                    "dinda fatimah",
                    "zendi ikilima",
                ]
            ):
                continue

            if re.search(
                r"show\s+\d+\s+per\s+page",
                lower
            ):
                continue

            if re.search(
                r"\d+\s*-\s*\d+\s+of\s+\d+",
                lower
            ):
                continue

            filtered_rows.append(row)

        result = filtered_rows

    if not result:
        return ""

    return "[Tabel]\n" + "\n".join(result)


def markdown_table_to_text(markdown):

    lines = markdown.splitlines()

    rows = []

    for line in lines:

        line = line.strip()

        if not line.startswith("|"):
            continue

        cells = [
            clean_table_cell(x)
            for x in line.strip("|").split("|")
        ]

        # Markdown separator
        if cells and all(
            re.fullmatch(
                r":?-{2,}:?",
                cell
            )
            for cell in cells
            if cell
        ):
            continue

        joined = " | ".join(cells)

        if re.search(
            r"show\s+\d+\s+per\s+page",
            joined,
            flags=re.I
        ):
            continue

        if re.search(
            r"\d+\s*-\s*\d+\s+of\s+\d+",
            joined,
            flags=re.I
        ):
            continue

        if any(cells):
            rows.append(joined)

    if not rows:
        return ""

    table_text = "\n".join(rows)

    if table_is_example_record(table_text):
        return ""

    if table_contains_example_personal_data(table_text):
        return ""

    if table_contains_ui_actions(table_text):

        filtered_rows = []

        for row in rows:

            lower = row.lower()

            if any(
                name in lower
                for name in [
                    "arrival dwi sentosa",
                    "dinda fatimah",
                    "zendi ikilima",
                ]
            ):
                continue

            filtered_rows.append(row)

        rows = filtered_rows

    if not rows:
        return ""

    return "[Tabel]\n" + "\n".join(rows)


def table_to_text(content):

    if not isinstance(content, str):
        return ""

    content = content.strip()

    if not content:
        return ""

    if "<table" in content.lower():

        return html_table_to_text(content)

    if (
        content.startswith("|")
        and "\n|" in content
    ):

        return markdown_table_to_text(
            content
        )

    return ""


# ============================================================
# BLOCK → TEXT
# ============================================================

def block_to_text(block):

    block_type = block.get("type")
    content = block.get("content", "")

    # -------------------------
    # TEXT
    # -------------------------

    if block_type == "text":

        if isinstance(content, str):

            text = clean_text(content)

            if looks_like_navigation_dump(text):
                return ""

            text = remove_ui_fragments(text)

            if not text:
                return ""

            return text

        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, dict):

                    value = item.get(
                        "content",
                        ""
                    )

                    if isinstance(value, str):
                        parts.append(value)

                elif isinstance(item, str):

                    parts.append(item)

            text = clean_text(
                " ".join(parts)
            )

            if looks_like_navigation_dump(text):
                return ""

            return remove_ui_fragments(text)

        return ""

    # -------------------------
    # IMAGE
    # -------------------------

    if block_type == "image":

        captions = block.get(
            "captions",
            []
        )

        caption_texts = []

        if isinstance(captions, list):

            for caption in captions:

                if not isinstance(caption, dict):
                    continue

                value = caption.get(
                    "content",
                    ""
                )

                if (
                    isinstance(value, str)
                    and value.strip()
                ):

                    value = clean_text(value)

                    if value:
                        caption_texts.append(value)

        if caption_texts:

            return (
                "[Gambar] "
                + " ".join(caption_texts)
            )

        return ""

    # -------------------------
    # TABLE
    # -------------------------

    if block_type == "table":

        table_text = table_to_text(content)

        if not table_text:
            return ""

        # Tabel screenshot aplikasi biasanya hanya
        # contoh data, bukan knowledge.
        if table_contains_example_personal_data(
            table_text
        ):
            return ""

        if table_contains_ui_actions(
            table_text
        ):
            return ""

        return table_text

    # -------------------------
    # OTHER
    # -------------------------

    if isinstance(content, str):

        text = clean_text(content)

        if looks_like_navigation_dump(text):
            return ""

        return text

    return ""

    block_type = block.get("type")
    content = block.get("content", "")

    # -------------------------
    # TEXT
    # -------------------------

    if block_type == "text":

        if isinstance(content, str):

            text = clean_text(content)

            if looks_like_navigation_dump(text):
                return ""

            text = remove_ui_fragments(text)

            if not text:
                return ""

            return text

        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, dict):

                    value = item.get(
                        "content",
                        ""
                    )

                    if isinstance(
                        value,
                        str
                    ):
                        parts.append(value)

                elif isinstance(item, str):

                    parts.append(item)

            text = clean_text(
                " ".join(parts)
            )

            if looks_like_navigation_dump(text):
                return ""

            return remove_ui_fragments(
                text
            )

        return ""

    # -------------------------
    # IMAGE
    # -------------------------

    if block_type == "image":

        captions = block.get(
            "captions",
            []
        )

        caption_texts = []

        if isinstance(
            captions,
            list
        ):

            for caption in captions:

                if not isinstance(
                    caption,
                    dict
                ):
                    continue

                value = caption.get(
                    "content",
                    ""
                )

                if (
                    isinstance(
                        value,
                        str
                    )
                    and value.strip()
                ):

                    value = clean_text(
                        value
                    )

                    if value:
                        caption_texts.append(
                            value
                        )

        if caption_texts:

            return (
                "[Gambar] "
                + " ".join(
                    caption_texts
                )
            )

        return ""

    # -------------------------
    # TABLE
    # -------------------------

# ============================================================
# SECTION DETECTION
# ============================================================

def is_main_section(title):

    if not title:
        return False

    return bool(
        re.match(
            r"^\d+[\.\)]\s+",
            title.strip()
        )
    )


def is_decorative_title(title):

    if not title:
        return False

    letters = [
        c
        for c in title
        if c.isalpha()
    ]

    if not letters:
        return False

    uppercase_ratio = (
        sum(
            c.isupper()
            for c in letters
        )
        / len(letters)
    )

    return (
        len(letters) >= 15
        and uppercase_ratio >= 0.80
    )


# ============================================================
# DOCUMENT PARSER
# ============================================================

def is_menu_fragment(text):
    """
    Mendeteksi potongan navigation/sidebar yang terpecah
    menjadi beberapa block oleh MinerU.
    """

    if not text:
        return False

    normalized = clean_text(text).lower()

    # Menu yang sering muncul pada sidebar PDF ini
    menu_patterns = [
        "dashboard",
        "profile mahasiswa",
        "pengajuan surat pengantar",
        "pengajuan surat keterangan lulus",
        "pendaftaran bimbingan proposal",
        "logbook mahasiswa bimbingan proposal",
        "pendaftaran sidang proposal",
        "hasil sidang proposal",
        "informasi sidang proposal",
        "pendaftaran bimbingan akhir",
        "logbook mahasiswa bimbingan akhir",
    ]

    # Exact / hampir exact menu item
    for pattern in menu_patterns:
        if normalized == pattern:
            return True

    # Block sangat pendek yang hanya terdiri dari
    # beberapa nama menu
    words = normalized.split()

    if len(words) <= 8:

        hits = sum(
            1
            for pattern in menu_patterns
            if pattern in normalized
        )

        if hits >= 1 and not re.search(
            r"[.!?]",
            normalized
        ):
            return True

    return False


def is_example_table_fragment(text):
    """
    Mendeteksi sisa tabel screenshot aplikasi.
    Tidak menghapus kalimat prosedural.
    """

    if not text:
        return False

    normalized = text.lower()

    # Pagination
    if re.search(
        r"show\s+\d+\s+per\s+page",
        normalized
    ):
        return True

    if re.search(
        r"\d+\s*-\s*\d+\s+of\s+\d+",
        normalized
    ):
        return True

    # UI action
    if re.search(
        r"\b(edit|delete|detail|print|action)\b",
        normalized
    ):
        return True

    return False


def parse_document(data):

    pages = data.get(
        "pages",
        []
    )

    sections = []

    current_section = None
    current_subsection = None
    current_items = []

    def flush_section():

        nonlocal current_items

        if not current_section:
            return

        if not current_items:
            return

        sections.append({
            "section": current_section,
            "items": current_items.copy()
        })

        current_items = []

    for page in pages:

        page_idx = page.get(
            "page_idx",
            0
        )

        page_number = (
            page_idx + 1
        )

        for block in page.get(
            "blocks",
            []
        ):

            block_type = block.get(
                "type"
            )

            # ----------------------------------------
            # Ignore page decoration
            # ----------------------------------------

            if block_type in {
                "header",
                "footer",
                "page_number"
            }:
                continue

            # ----------------------------------------
            # TITLES
            # ----------------------------------------

            if block_type == "paragraph_title":

                title = clean_text(
                    block.get(
                        "content",
                        ""
                    )
                )

                if not title:
                    continue

                # Main numbered section
                if is_main_section(
                    title
                ):

                    flush_section()

                    current_section = title
                    current_subsection = None

                    continue

                # Decorative uppercase title
                if is_decorative_title(
                    title
                ):
                    continue

                # Navigation menu
                if is_menu_fragment(
                    title
                ):
                    continue

                # Subsection
                if current_section:

                    current_subsection = title

                    current_items.append({
                        "page":
                            page_number,

                        "subsection":
                            current_subsection,

                        "text":
                            f"[Subsection] {title}"
                    })

                continue

            # ----------------------------------------
            # NORMAL BLOCK
            # ----------------------------------------

            text = block_to_text(
                block
            )

            if not text:
                continue

            if not current_section:
                continue

            # Remove navigation fragments
            if is_menu_fragment(
                text
            ):
                continue

            # Remove obvious table/UI fragments
            if is_example_table_fragment(
                text
            ):
                continue

            text = remove_ui_fragments(
                text
            )

            if not text:
                continue

            current_items.append({
                "page":
                    page_number,

                "subsection":
                    current_subsection,

                "text":
                    text
            })

    flush_section()

    return sections

# ============================================================
# TOKEN CHUNKING
# ============================================================

def tokenize(text):

    return tokenizer.encode(
        text,
        add_special_tokens=False
    )


def detokenize(token_ids):

    return tokenizer.decode(
        token_ids,
        skip_special_tokens=True
    )


def create_token_chunks(
    section_data
):

    section_name = (
        section_data["section"]
    )

    items = section_data["items"]

    chunks = []

    current_tokens = []
    current_pages = []
    current_subsections = []

    def flush():

        nonlocal current_tokens
        nonlocal current_pages
        nonlocal current_subsections

        if not current_tokens:
            return

        text = detokenize(
            current_tokens
        ).strip()

        if not text:
            return

        chunks.append({

            "section":
                section_name,

            "subsections":
                list(
                    dict.fromkeys(
                        current_subsections
                    )
                ),

            "page_start":
                min(current_pages),

            "page_end":
                max(current_pages),

            "text":
                text,

            "token_count":
                len(current_tokens)
        })

        if CHUNK_OVERLAP > 0:

            current_tokens = (
                current_tokens[
                    -CHUNK_OVERLAP:
                ]
            )

            current_pages = (
                current_pages[-1:]
                if current_pages
                else []
            )

            current_subsections = (
                current_subsections[-1:]
                if current_subsections
                else []
            )

        else:

            current_tokens = []
            current_pages = []
            current_subsections = []

    for item in items:

        item_text = item["text"]

        item_tokens = tokenize(
            item_text
        )

        if not item_tokens:
            continue

        item_page = item["page"]

        item_subsection = (
            item.get(
                "subsection"
            )
        )

        # Large item
        if len(item_tokens) > CHUNK_SIZE:

            flush()

            start = 0

            while start < len(
                item_tokens
            ):

                end = min(
                    start + CHUNK_SIZE,
                    len(item_tokens)
                )

                part = item_tokens[
                    start:end
                ]

                text = detokenize(
                    part
                ).strip()

                chunks.append({

                    "section":
                        section_name,

                    "subsections":
                        (
                            [item_subsection]
                            if item_subsection
                            else []
                        ),

                    "page_start":
                        item_page,

                    "page_end":
                        item_page,

                    "text":
                        text,

                    "token_count":
                        len(part)
                })

                if end >= len(
                    item_tokens
                ):
                    break

                start = (
                    end
                    - CHUNK_OVERLAP
                )

            continue

        # Overflow
        if (
            len(current_tokens)
            + len(item_tokens)
            > CHUNK_SIZE
        ):

            flush()

        current_tokens.extend(
            item_tokens
        )

        current_pages.append(
            item_page
        )

        if item_subsection:

            current_subsections.append(
                item_subsection
            )

    flush()

    return chunks


# ============================================================
# FINAL CHUNKS
# ============================================================

def build_final_chunks(
    sections
):

    final_chunks = []

    number = 0

    for section in sections:

        chunks = create_token_chunks(
            section
        )

        for chunk in chunks:

            number += 1

            final_chunks.append({

                "chunk_id":
                    f"{DOCUMENT_ID}_{FILE_ID}_{number:03d}",

                "document_id":
                    DOCUMENT_ID,

                "file_id":
                    FILE_ID,

                "category_id":
                    CATEGORY_ID,

                "category_name":
                    CATEGORY_NAME,

                "document_title":
                    DOCUMENT_TITLE,

                "section":
                    chunk["section"],

                "subsections":
                    chunk["subsections"],

                "page_start":
                    chunk["page_start"],

                "page_end":
                    chunk["page_end"],

                "chunk_number":
                    number,

                "token_count":
                    chunk["token_count"],

                "text":
                    chunk["text"]
            })


    return final_chunks


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("MinerU Parser V4.2")
    print("=" * 60)

    if not INPUT_JSON.exists():

        print(
            f"ERROR: {INPUT_JSON} tidak ditemukan."
        )

        return

    with open(
        INPUT_JSON,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    pages = data.get(
        "pages",
        []
    )

    print(
        f"Pages              : {len(pages)}"
    )

    sections = parse_document(
        data
    )

    print(
        f"Sections            : {len(sections)}"
    )

    chunks = build_final_chunks(
        sections
    )

    print(
        f"Final chunks        : {len(chunks)}"
    )

    print(
        f"Chunk target        : {CHUNK_SIZE} tokens"
    )

    print(
        f"Chunk overlap       : {CHUNK_OVERLAP} tokens"
    )

    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            chunks,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"Output              : {OUTPUT_JSON}"
    )

    print()
    print("=" * 60)
    print("PREVIEW")
    print("=" * 60)

    for chunk in chunks:

        print()

        print(
            f"[Chunk {chunk['chunk_number']}] "
            f"Page {chunk['page_start']}-"
            f"{chunk['page_end']}"
        )

        print(
            f"Section : {chunk['section']}"
        )

        print(
            f"Tokens  : {chunk['token_count']}"
        )

        print(
            f"Subsec  : {chunk['subsections']}"
        )

        preview = chunk["text"]

        if len(preview) > 700:

            preview = (
                preview[:700]
                + "..."
            )

        print(
            "Text    : "
            + preview.replace(
                "\n",
                "\n          "
            )
        )

        print("-" * 60)


if __name__ == "__main__":
    main()
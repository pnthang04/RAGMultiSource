import pandas as pd
from markitdown import MarkItDown
from markitdown._exceptions import FileConversionException
import tempfile
import os
import json

def _read_base_csv(path: str):
    df = pd.read_csv(path, encoding="latin1")
    descriptions = []
    for _, row in df.iterrows():
        desc = " . ".join([f"{col} là {row[col]}" for col in df.columns])
        descriptions.append(desc)
    return "\n".join(descriptions)

def convert_with_ignore_encoding(path):
    md = MarkItDown()

    try:
        return md.convert(path)

    except FileConversionException:
        pass

    with open(path, "rb") as f:
        content = f.read()

    text = content.decode("utf-8", errors="ignore")

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False
    ) as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    try:
        return md.convert(tmp_path).markdown
    finally:
        os.remove(tmp_path)

def read_full_csv(path, to_markdown=True):
    if to_markdown:
        return convert_with_ignore_encoding(path)
    
    return _read_base_csv(path)

def read_csv(path, k=5):
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin1")
    
    result = {
        "metadata": {
            "file_name": os.path.basename(path),
            "file_size": os.path.getsize(path)
        },
        "num_columns": len(df.columns),
        "num_rows": len(df),
        "first_k_rows": df.head(k).to_dict(orient="records")
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
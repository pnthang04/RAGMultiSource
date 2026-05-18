from pathlib import Path


class DoclingMarkdownConverter:
    def convert_to_markdown(self, input_path: str, output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(input_path)
            markdown = result.document.export_to_markdown()
        except Exception:
            with open(input_path, "rb") as f:
                raw_bytes = f.read()
            markdown = raw_bytes.decode("utf-8", errors="ignore")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        return output_path

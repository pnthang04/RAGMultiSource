from markitdown import MarkItDown
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

def iter_block_items(parent):
    for child in parent.element.body:
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _read_base_word(path):
    doc = Document(path)
    texts = []
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                texts.append(text)
               
        elif isinstance(block, Table):
            table_data = []
            for row in block.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_data.append(row_cells)

            if table_data:
                header_row = table_data[0]
                md_table_blocks = []
                for row in table_data[1:]:
                                                                         
                    row_items = []
                    for i in range(len(header_row)):
                        header_name = header_row[i].strip() if (i < len(header_row) and header_row[i]) else f"Col{i}"
                        cell_value = row[i].strip() if i < len(row) else ""
                        row_items.append(f"{header_name} là {cell_value}")

                    row_str = " . ".join(row_items)
                    md_table_blocks.append(row_str)

                texts.append("\n<start_table>\n" + "\n".join(md_table_blocks) + "\n<end_table>\n")

    return "\n".join(texts)

def _read_to_markdown(path):
    md = MarkItDown()
    return md.convert(path).markdown

def read_full_word(path, to_markdown=True):
    if to_markdown:
        return _read_to_markdown(path)
    
    return _read_base_word(path)
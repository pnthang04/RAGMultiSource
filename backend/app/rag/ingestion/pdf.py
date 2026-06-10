import fitz
import os
from markitdown import MarkItDown

def _read_base_pdf(path):
    final_output = []
    doc = fitz.open(path)

    for page in doc:
        page_elements = []                                 
        tables = page.find_tables()
        table_bboxes = []

                                                 
        if tables.tables:
            for table in tables.tables:
                table_bboxes.append(table.bbox)
                extracted = table.extract()
                                
                clean_rows = []
                for row in extracted:
                    if row:
                        clean_rows.append([(cell.strip().replace("\n", " ") if cell else "") for cell in row])
                if clean_rows:
                    header_row = clean_rows[0]
                    md_table_blocks = []
                                                                
                    for row in clean_rows[1:]:
                        row_items = []
                        for i in range(len(header_row)):
                            header_name = header_row[i].strip() if (i < len(header_row) and header_row[i]) else f"Col{i}"
                            cell_value = row[i].strip() if i < len(row) else ""
                            row_items.append(f"{header_name} là {cell_value}")

                        row_str = " . ".join(row_items)
                        md_table_blocks.append(row_str)

                                                                            
                    page_elements.append({
                        "y": table.bbox[1],
                        "content": "\n<start_table>\n" + "\n".join(md_table_blocks) + "\n<end_table>\n",
                        "type": "table"
                    })

                                                        
        blocks = page.get_text("blocks", sort=False)                                
        for block in blocks:
            if block[6] != 0: continue               

            x0, y0, x1, y1, text, block_no, block_type = block

                                                                              
            is_inside_table = False
            for bx0, by0, bx1, by1 in table_bboxes:
                if y0 >= by0 - 2 and y1 <= by1 + 2:                                  
                    is_inside_table = True
                    break

            if not is_inside_table:
                clean_text = text.strip()
                if clean_text:
                    page_elements.append({
                        "y": y0,
                        "content": clean_text,
                        "type": "text"
                    })

                                                                                
        page_elements.sort(key=lambda x: x["y"])

        for el in page_elements:
            final_output.append(el["content"])

    doc.close()
    if final_output:
        return "\n\n".join(final_output)

    return ""


def _read_to_markdown(path):
    md = MarkItDown()
    result = md.convert(path)
    return result.text_content


def read_full_pdf(path: str, to_markdown=True):
    if to_markdown:
        return _read_to_markdown(path)
    
    return _read_base_pdf(path)
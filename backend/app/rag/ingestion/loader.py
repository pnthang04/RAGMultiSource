import os
from backend.app.rag.ingestion import pdf, word, csv, excel, image

class Loader:
    def __init__(self):
        self.document = None
    
    def _read_word(self, path, to_markdown=True):
        self.document = word.read_full_word(path, to_markdown=to_markdown)
    
    def _read_pdf(self, path, to_markdown=True):
        self.document = pdf.read_full_pdf(path, to_markdown=to_markdown)
        
    def _read_csv(self, path, to_markdown=True):
        self.document = csv.read_full_csv(path, to_markdown=to_markdown)

    def _read_excel(self, path, to_markdown=True):
        self.document = excel.read_full_excel(path, to_markdown=to_markdown)
    
    def _read_image(self, path, to_markdown=True):
        self.document = image.read_image(path, to_markdown=to_markdown)

    def read(self, path, to_markdown=True):
        ext = os.path.splitext(path)[-1].lower()
        if ext in ['.pdf']:
            self._read_pdf(path, to_markdown=to_markdown)
        elif ext in ['.docx', '.doc']:
            self._read_word(path, to_markdown=to_markdown)
        elif ext in ['.csv']:
            self._read_csv(path, to_markdown=to_markdown)
        elif ext in ['.xlsx', '.xls']:
            self._read_excel(path, to_markdown=to_markdown)
        elif ext in ['.png', '.jpg', '.jpeg']:
            self._read_image(path, to_markdown=to_markdown)
        else:
            self.document = None
        return self.document
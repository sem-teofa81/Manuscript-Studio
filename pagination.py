"""Print pagination helpers for right-hand (recto) chapter starts."""
from reportlab.platypus.doctemplate import ActionFlowable

class ChapterPageBreak(ActionFlowable):
    """Start a chapter on a fresh page; optionally require an odd-numbered recto."""
    def __init__(self, recto=True, first=False):
        ActionFlowable.__init__(self, ('chapterPageBreak',))
        self.recto=recto
        self.first=first

    def apply(self, doc):
        # If already at top, do not add a redundant blank page.
        at_top=bool(getattr(doc.frame,'_atTop',False))
        if not at_top:
            doc.handle_pageBreak()
        if self.recto and doc.page % 2 == 0:
            if not hasattr(doc,'_blank_verso_pages'):
                doc._blank_verso_pages=set()
            doc._blank_verso_pages.add(doc.page)
            doc.handle_pageBreak()
        if self.first:
            doc._body_start_page=doc.page

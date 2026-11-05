"""Front matter, dynamic PDF table of contents and standalone front-cover draft."""
import io
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

def title_page(opts,w,h):
    title=escape(opts.get('title','Manoscritto'))
    subtitle=escape(opts.get('subtitle',''))
    author=escape(opts.get('author',''))
    center=ParagraphStyle('FrontTitle',fontName='KDPSerif-Bold',fontSize=21,leading=29,alignment=TA_CENTER,spaceAfter=22)
    small=ParagraphStyle('FrontSmall',fontName='KDPSerif',fontSize=12,leading=17,alignment=TA_CENTER,spaceAfter=15)
    content=[Spacer(1,max(65,h*.22)),Paragraph(title,center)]
    if subtitle:content.append(Paragraph(subtitle,small))
    if author:content.extend([Spacer(1,40),Paragraph(author,small)])
    content.append(PageBreak())
    return content

def copyright_page(opts):
    style=ParagraphStyle('CopyrightPage',fontName='KDPSerif',fontSize=9,leading=15)
    lines=[f"© {escape(str(opts.get('year','')))} {escape(opts.get('author',''))}".strip(),
           'Tutti i diritti riservati.',
           'Nessuna parte di questo libro può essere riprodotta senza autorizzazione, salvo quanto consentito dalla legge.']
    if opts.get('isbn'):lines.append('ISBN: '+escape(opts['isbn']))
    if opts.get('edition'):lines.append(escape(opts['edition']))
    if opts.get('copyright_note'):lines.append(escape(opts['copyright_note']))
    return [Spacer(1,120)]+[Paragraph(t,style) for t in lines]+[PageBreak()]

def pdf_toc():
    toc=TableOfContents()
    toc.levelStyles=[
        ParagraphStyle('TOC1',fontName='KDPSerif',fontSize=10,leading=16,leftIndent=0,firstLineIndent=0,spaceAfter=5),
        ParagraphStyle('TOC2',fontName='KDPSerif',fontSize=9,leading=14,leftIndent=16,firstLineIndent=0,spaceAfter=3)]
    heading=Paragraph('Indice',ParagraphStyle('TOCTitle',fontName='KDPSerif-Bold',fontSize=19,leading=26,spaceAfter=24))
    return toc,[heading,toc,PageBreak()]

class IndexedDocTemplate(SimpleDocTemplate):
    def afterFlowable(self,flowable):
        if not isinstance(flowable,Paragraph):return
        if not getattr(flowable,'_toc_level',None):return
        level=flowable._toc_level-1
        text=flowable.getPlainText()
        key=f'heading-{self.seq.nextf("heading")}'
        self.canv.bookmarkPage(key)
        self.notify('TOCEntry',(level,text,self.page,key))

def export_front_cover(opts):
    """Separate FRONT COVER DRAFT ONLY: no spine/back/bleed; not a KDP upload-ready wrap."""
    w=float(opts.get('width',6))*inch;h=float(opts.get('height',9))*inch
    out=io.BytesIO();c=Canvas(out,pagesize=(w,h))
    c.setFillColorRGB(.91,.95,.94);c.rect(0,0,w,h,stroke=0,fill=1)
    c.setFillColorRGB(.15,.29,.33)
    c.rect(28,28,w-56,h-56,stroke=1,fill=0)
    def centered_wrapped(text,y,font,size,maxw):
        words=str(text).split();lines=[];line=''
        for word in words:
            trial=(line+' '+word).strip()
            if line and pdfmetrics.stringWidth(trial,font,size)>maxw:
                lines.append(line);line=word
            else:line=trial
        if line:lines.append(line)
        for ln in lines:
            c.setFont(font,size);c.drawCentredString(w/2,y,ln);y-=size*1.35
        return y
    y=centered_wrapped(opts.get('title','Manoscritto'),h*.70,'KDPSerif-Bold',24,w-90)
    if opts.get('subtitle'):centered_wrapped(opts['subtitle'],y-32,'KDPSerif',13,w-95)
    if opts.get('author'):centered_wrapped(opts['author'],h*.23,'KDPSerif-Bold',14,w-90)
    c.showPage();c.save()
    return out.getvalue()

"""Structured manuscript model, import, editable styles and print PDF rendering."""
import io, re, copy
from dataclasses import dataclass, asdict
from xml.sax.saxutils import escape
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem, Table, TableStyle, KeepTogether, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
if not 'KDPSerif' in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont('KDPSerif',FONT))
    pdfmetrics.registerFont(TTFont('KDPSerif-Bold',BOLD))
    pdfmetrics.registerFontFamily('KDPSerif',normal='KDPSerif',bold='KDPSerif-Bold')

BULLETS={'Pallino':'•','Quadratino':'▪','Trattino':'–','Cerchio':'○','Freccia':'›'}

def block(kind,text='',level=0,items=None):
    return {'kind':kind,'text':text,'level':level,'items':items or []}

def import_docx(raw):
    doc=Document(io.BytesIO(raw)); out=[]
    for el in doc.element.body:
        if el.tag.endswith('}p'):
            from docx.text.paragraph import Paragraph as DocParagraph
            p=DocParagraph(el,doc); txt=p.text.strip()
            if not txt: continue
            style=p.style.name.lower() if p.style else ''
            m=re.search(r'(?:heading|titolo|intestazione)\s*(\d)',style)
            if m: out.append(block('heading',txt,int(m.group(1)))); continue
            num=p._p.xpath('./w:pPr/w:numPr')
            if num or 'list bullet' in style or 'elenco puntato' in style:
                out.append(block('bullet',txt));continue
            if 'list number' in style or 'elenco numerato' in style:
                out.append(block('number',txt));continue
            if re.match(r'^\s*[│├└─+|]',txt):out.append(block('paragraph',txt));continue
            out.append(block('paragraph',txt))
        elif el.tag.endswith('}tbl'):
            from docx.table import Table as DocTable
            t=DocTable(el,doc); rows=[[c.text.strip() for c in row.cells] for row in t.rows]
            out.append(block('table',items=rows))
    return out

def import_google_doc(data):
    out=[]
    for el in data.get('body',{}).get('content',[]):
        if 'paragraph' in el:
            p=el['paragraph']; txt=''.join(x.get('textRun',{}).get('content','') for x in p.get('elements',[])).strip()
            if not txt:continue
            typ=p.get('paragraphStyle',{}).get('namedStyleType','NORMAL_TEXT')
            if typ.startswith('HEADING_'):out.append(block('heading',txt,int(typ[-1])))
            elif p.get('bullet'):out.append(block('bullet',txt))
            else:out.append(block('paragraph',txt))
        elif 'table' in el:
            rows=[]
            for row in el['table'].get('tableRows',[]):
                vals=[]
                for cell in row.get('tableCells',[]):
                    vals.append(' '.join(x.get('textRun',{}).get('content','').strip() for p in cell.get('content',[]) for x in p.get('paragraph',{}).get('elements',[])))
                rows.append(vals)
            out.append(block('table',items=rows))
    return out

def chapters(blocks):
    indexes=[i for i,b in enumerate(blocks) if b['kind']=='heading' and b['level']==1]
    if not indexes:return [('Manoscritto',0,len(blocks))]
    starts=([0] if indexes[0]>0 else [])+indexes
    return [(('Introduzione' if s==0 and s!=indexes[0] else blocks[s]['text']),s, starts[j+1] if j+1<len(starts) else len(blocks)) for j,s in enumerate(starts)]

from diagrams import parse_tree, tree_drawing, flow_drawing
from frontmatter import title_page, copyright_page, pdf_toc, IndexedDocTemplate

def export_pdf(blocks,opts):
    buf=io.BytesIO();page_width=float(opts.get('width',6))*inch;page_height=float(opts.get('height',9))*inch
    margin=float(opts.get('margin',0.7))*inch
    pdf=IndexedDocTemplate(buf,pagesize=(page_width,page_height),leftMargin=margin,rightMargin=margin,topMargin=margin,bottomMargin=margin, title=opts.get('title','Manoscritto'))
    base=float(opts.get('font_size',9.5));leading=base*1.45
    styles={
      'body':ParagraphStyle('BodyKDP',fontName='KDPSerif',fontSize=base,leading=leading,alignment=TA_JUSTIFY,spaceAfter=8),
      'bullet':ParagraphStyle('BulletKDP',fontName='KDPSerif',fontSize=base,leading=leading,leftIndent=18,firstLineIndent=-13,spaceAfter=4),
      'number':ParagraphStyle('NumberKDP',fontName='KDPSerif',fontSize=base,leading=leading,leftIndent=18,firstLineIndent=-13,spaceAfter=4),
    }
    for i in range(1,7):
        styles[f'h{i}']=ParagraphStyle(f'Heading{i}KDP',fontName='KDPSerif-Bold',fontSize=max(base+1,19-2*(i-1)),leading=max(base+4,23-2*(i-1)),spaceBefore=15 if i==1 else 10,spaceAfter=9,keepWithNext=True)
    story=[];number=0
    available_height=page_height-2*margin
    if opts.get('title_page',True):story.extend(title_page(opts,page_width-2*margin,available_height))
    if opts.get('copyright_page',True):story.extend(copyright_page(opts))
    if opts.get('toc',True):
        toc,parts=pdf_toc();story.extend(parts)
    for idx,b in enumerate(blocks):
        typ=b.get('kind','paragraph');txt=escape(b.get('text','')).replace('\n','<br/>')
        if typ=='heading':
            lvl=min(6,max(1,int(b.get('level',1))))
            if lvl==1 and opts.get('chapter_breaks',True) and story:story.append(PageBreak())
            heading=Paragraph(txt,styles[f'h{lvl}'])
            if lvl<=2:heading._toc_level=lvl
            story.append(heading)
        elif typ=='paragraph':story.append(Paragraph(txt,styles['body']))
        elif typ=='bullet':story.append(Paragraph(escape(BULLETS.get(opts.get('bullet','Pallino'),'•'))+'  '+txt,styles['bullet']))
        elif typ=='number':
            number+=1;story.append(Paragraph(f'{number}.  '+txt,styles['number']))
        elif typ in ('tree','flow'):
            available=page_width-2*margin-12
            drawing=tree_drawing(b.get('text',''),available) if typ=='tree' else flow_drawing(b.get('text',''),available)
            story.append(drawing);story.append(Spacer(1,9))
        elif typ=='table':
            rows=b.get('items',[])
            if rows:
                n=max(map(len,rows));cellstyle=ParagraphStyle('Cell',fontName='KDPSerif',fontSize=base-1,leading=leading-1)
                data=[[Paragraph(escape(str(row[j] if j<len(row) else '')),cellstyle) for j in range(n)] for row in rows]
                t=Table(data,colWidths=[(page_width-2*margin)/n]*n,repeatRows=1,hAlign='LEFT')
                t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.35,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9F1F4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
                story.append(t);story.append(Spacer(1,10))
    def footer(canvas,doc):
        canvas.setFont('KDPSerif',8);canvas.drawCentredString(page_width/2,margin*.55,str(doc.page))
    pdf.multiBuild(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()

def export_docx(blocks,opts):
    doc=Document();section=doc.sections[0]
    section.page_width=int(float(opts.get('width',6))*914400);section.page_height=int(float(opts.get('height',9))*914400)
    for k in ('top_margin','bottom_margin','left_margin','right_margin'):setattr(section,k,int(float(opts.get('margin',.7))*914400))
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    normal=doc.styles['Normal'];normal.font.name='DejaVu Serif';normal.font.size=Pt(float(opts.get('font_size',9.5)))
    if opts.get('title_page',True):
        doc.add_paragraph('\\n'*5)
        p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        r=p.add_run(opts.get('title','Manoscritto'));r.bold=True;r.font.size=Pt(22)
        for key in ('subtitle','author'):
            if opts.get(key):
                p=doc.add_paragraph(opts[key]);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        doc.add_page_break()
    if opts.get('copyright_page',True):
        doc.add_paragraph('© '+str(opts.get('year',''))+' '+opts.get('author',''))
        doc.add_paragraph('Tutti i diritti riservati.')
        if opts.get('isbn'):doc.add_paragraph('ISBN: '+opts['isbn'])
        if opts.get('edition'):doc.add_paragraph(opts['edition'])
        if opts.get('copyright_note'):doc.add_paragraph(opts['copyright_note'])
        doc.add_page_break()
    if opts.get('toc',True):
        doc.add_heading('Indice',0)
        p=doc.add_paragraph()
        fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'TOC \\o "1-2" \\h \\z \\u')
        p._p.append(fld)
        doc.add_page_break()
    for b in blocks:
        typ=b.get('kind');txt=b.get('text','')
        if typ=='heading':
            p=doc.add_paragraph(txt,style=f'Heading {min(6,max(1,int(b.get("level",1))))}')
            if b.get('level')==1 and opts.get('chapter_breaks',True):p.paragraph_format.page_break_before=True
        elif typ=='bullet':doc.add_paragraph(BULLETS.get(opts.get('bullet','Pallino'),'•')+'  '+txt)
        elif typ=='number':doc.add_paragraph(txt,style='List Number')
        elif typ=='table':
            rows=b.get('items',[])
            if rows:
                t=doc.add_table(rows=len(rows),cols=max(map(len,rows)));t.style='Table Grid'
                for i,row in enumerate(rows):
                    for j,val in enumerate(row):t.cell(i,j).text=str(val)
        elif typ in ('tree','flow'):
            # Word receives the same graphical diagram as PDF when rasterization is available.
            try:
                from reportlab.graphics import renderPM
                from docx.shared import Inches
                drawing=tree_drawing(txt,320) if typ=='tree' else flow_drawing(txt,320)
                image=io.BytesIO(renderPM.drawToString(drawing,fmt='PNG',dpi=160))
                p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(image,width=Inches(min(4.4,float(opts.get('width',6))-2*float(opts.get('margin',.7)))))
            except Exception:
                doc.add_paragraph(txt)
        else:doc.add_paragraph(txt)
    out=io.BytesIO();doc.save(out);return out.getvalue()

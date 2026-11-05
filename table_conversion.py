"""Conservative detection of text tables in imported manuscripts."""
import re

def _cells(text):
    text=text.strip()
    if not text:return None
    if '\t' in text:
        cells=[c.strip() for c in text.split('\t')]
    elif '|' in text:
        cells=[c.strip() for c in text.strip('|').split('|')]
    elif '│' in text:
        cells=[c.strip() for c in text.strip('│').split('│')]
    else:return None
    return cells if len(cells)>=2 and all(cells) else None

def _separator(cells):
    return all(re.fullmatch(r':?-{3,}:?',c.strip()) for c in cells)

def convert_tables(blocks):
    """Convert adjacent pipe/tab-separated paragraphs or multiline markdown tables.

    A candidate needs at least two rows of the same width. Other text is untouched.
    Existing Word/Google Docs table blocks are already structured and not modified.
    """
    result=[];i=0;count=0
    while i<len(blocks):
        b=blocks[i]
        if b.get('kind')!='paragraph':
            result.append(b);i+=1;continue
        raw=b.get('text','')
        lines=[s for s in raw.splitlines() if s.strip()]
        if len(lines)>=2:
            parsed=[_cells(s) for s in lines]
            usable=[row for row in parsed if row is not None and not _separator(row)]
            if all(row is not None for row in parsed) and len(usable)>=2 and len({len(row) for row in usable})==1:
                result.append({'kind':'table','text':'','level':0,'items':usable});count+=1;i+=1;continue
        first=_cells(raw)
        if not first or _separator(first):
            result.append(b);i+=1;continue
        rows=[first];j=i+1
        while j<len(blocks) and blocks[j].get('kind')=='paragraph':
            value=blocks[j].get('text','')
            if '\n' in value.strip():break
            row=_cells(value)
            if row is None or len(row)!=len(first):break
            if not _separator(row):rows.append(row)
            j+=1
        if len(rows)>=2:
            result.append({'kind':'table','text':'','level':0,'items':rows});count+=1;i=j
        else:result.append(b);i+=1
    return result,count

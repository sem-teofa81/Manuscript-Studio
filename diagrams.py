"""Vector diagrams for print: hierarchical trees and linear decision flowcharts."""
import re, textwrap
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

INK=colors.HexColor('#283F4B')
ACCENT=colors.HexColor('#4B8394')
PALE=colors.HexColor('#EDF5F7')
WHITE=colors.white

def _lines(label,max_width,font=8):
    words=str(label).split()
    lines=[];line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if line and pdfmetrics.stringWidth(candidate,'KDPSerif',font)>max_width:
            lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    return lines or ['']

def _text(d,lines,cx,cy,font=8):
    spacing=font*1.32
    for j,line in enumerate(lines):
        d.add(String(cx,cy+(len(lines)-1)*spacing/2-j*spacing,line,textAnchor='middle',fontName='KDPSerif',fontSize=font,fillColor=INK))

def _arrow(d,x1,y1,x2,y2):
    d.add(Line(x1,y1,x2,y2,strokeColor=ACCENT,strokeWidth=1.15))
    import math
    angle=math.atan2(y2-y1,x2-x1)
    a=5
    pts=[x2,y2,x2-a*math.cos(angle-.5),y2-a*math.sin(angle-.5),x2-a*math.cos(angle+.5),y2-a*math.sin(angle+.5)]
    d.add(Polygon(pts,fillColor=ACCENT,strokeColor=ACCENT))

def parse_tree(text):
    roots=[];stack=[]
    for raw in text.splitlines():
        if not raw.strip():continue
        expanded=raw.expandtabs(4)
        match=re.match(r'^(\s*(?:[│ ]{0,4})*(?:├──|└──|\+--)?\s*)',expanded)
        prefix=match.group(0)
        label=expanded[len(prefix):].strip()
        if not label:continue
        if '├──' in prefix or '└──' in prefix:
            depth=prefix.count('│')+prefix.count('    ')+1
        else:depth=len(prefix)//4
        if depth>len(stack):depth=len(stack)
        node={'label':label,'children':[]}
        if depth and stack:stack[depth-1]['children'].append(node)
        else:roots.append(node)
        stack=stack[:depth]+[node]
    return roots

def tree_drawing(text,width=330):
    roots=parse_tree(text)
    if not roots:return Drawing(width,30)
    entries=[]
    def visit(nodes,depth,parent=None):
        for n in nodes:
            idx=len(entries);entries.append((n,depth,parent))
            visit(n['children'],depth+1,idx)
    visit(roots,0)
    maxdepth=max(e[1] for e in entries)
    # Compact vertical layout with wrapped labels and elbow connectors.
    indent=min(29,max(15,(width-115)/max(1,maxdepth)))
    heights=[];lines=[]
    for n,depth,_ in entries:
        available=max(60,width-16-depth*indent)
        ls=_lines(n['label'],available-20)
        lines.append(ls);heights.append(max(28,16+len(ls)*11))
    gap=12;height=sum(heights)+gap*(len(entries)-1)+12
    d=Drawing(width,height)
    y=height-6;centers=[]
    for i,(n,depth,parent) in enumerate(entries):
        h=heights[i];y-=h
        x=6+depth*indent;w=width-x-6
        d.add(Rect(x,y,w,h,rx=5,ry=5,fillColor=PALE if depth==0 else WHITE,strokeColor=ACCENT,strokeWidth=.8))
        _text(d,lines[i],x+w/2,y+h/2-3)
        centers.append((x,y+h/2,w,h))
        y-=gap
    # Draw elbow connectors after nodes; routes remain outside text boxes.
    for i,(_,depth,parent) in enumerate(entries):
        if parent is None:continue
        px,py,pw,_=centers[parent];x,cy,_,_=centers[i]
        startx=px+8;mid=x-7
        d.add(Line(startx,py-14,startx,cy,strokeColor=ACCENT,strokeWidth=.85))
        _arrow(d,startx,cy,x,cy)
    return d

def parse_flow(text):
    """One node per line: START:, END:, ACTION:, DECISION: question | yes | no.
    A decision has labeled outgoing paths; branches rejoin before the next step.
    """
    nodes=[]
    for raw in text.splitlines():
        raw=raw.strip()
        if not raw:continue
        m=re.match(r'^(START|END|ACTION|DECISION|INIZIO|FINE|AZIONE|DECISIONE)\s*:\s*(.*)$',raw,re.I)
        if not m:nodes.append(('action',raw,[]));continue
        typ={'inizio':'start','fine':'end','azione':'action','decisione':'decision'}.get(m.group(1).lower(),m.group(1).lower())
        parts=[x.strip() for x in m.group(2).split('|')]
        nodes.append((typ,parts[0],parts[1:]))
    return nodes

def flow_drawing(text,width=330):
    nodes=parse_flow(text)
    if not nodes:return Drawing(width,30)
    pad=8;boxw=min(230,width-72);cx=width/2
    details=[];heights=[]
    for typ,label,branches in nodes:
        ls=_lines(label,boxw-40,8)
        h=max(38,20+len(ls)*12)
        if typ=='decision':h=max(62,h+16)
        details.append(ls);heights.append(h)
    gap=32
    height=pad*2+sum(heights)+gap*(len(nodes)-1)
    d=Drawing(width,height)
    y=height-pad;positions=[]
    for i,(typ,label,branches) in enumerate(nodes):
        h=heights[i];y-=h;cy=y+h/2
        if typ=='decision':
            pts=[cx,cy+h/2,cx+boxw/2,cy,cx,cy-h/2,cx-boxw/2,cy]
            d.add(Polygon(pts,fillColor=PALE,strokeColor=ACCENT,strokeWidth=1.2))
            _text(d,details[i],cx,cy-3)
        else:
            rad=h/2 if typ in ('start','end') else 6
            d.add(Rect(cx-boxw/2,y,boxw,h,rx=rad,ry=rad,fillColor=PALE if typ in ('start','end') else WHITE,strokeColor=ACCENT,strokeWidth=1.1))
            _text(d,details[i],cx,cy-3)
        positions.append((y,h,cy))
        y-=gap
    for i,(typ,label,branches) in enumerate(nodes[:-1]):
        y,h,cy=positions[i];next_y,next_h,next_cy=positions[i+1]
        _arrow(d,cx,y,cx,next_y+next_h)
        if typ=='decision':
            # Branch labels only; do not invent branch destinations.
            yes=branches[0] if len(branches)>0 else 'Sì'
            no=branches[1] if len(branches)>1 else 'No'
            left=cx-boxw/2-4;right=cx+boxw/2+4
            d.add(String(max(4,left-24),cy-3,yes[:18],fontName='KDPSerif',fontSize=7,fillColor=INK))
            d.add(String(min(width-50,right+3),cy-3,no[:18],fontName='KDPSerif',fontSize=7,fillColor=INK))
    return d

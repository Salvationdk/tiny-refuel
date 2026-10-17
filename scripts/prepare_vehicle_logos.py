"""Strict sanitizer for locally supplied, reviewed make-logo SVG files."""
import xml.etree.ElementTree as ET
import re

def sanitize_svg(svg):
    if len(svg)>200000 or re.search(r'<!DOCTYPE|<!ENTITY',svg,re.I):
        raise ValueError('Unsupported SVG document')
    root=ET.fromstring(svg)
    allowed={'svg','path','g','title','desc','circle','ellipse','rect','polygon','polyline','line'}
    attrs={'viewBox','width','height','d','fill','fill-rule','clip-rule','transform','cx','cy','r','rx','ry','x','y','x1','y1','x2','y2','points','stroke','stroke-width','stroke-linecap','stroke-linejoin','role','opacity'}
    if root.tag.rsplit('}',1)[-1]!='svg' or not root.get('viewBox'):
        raise ValueError('SVG requires a viewBox')
    for e in root.iter():
        tag=e.tag.rsplit('}',1)[-1]
        if tag not in allowed: raise ValueError('Unsupported SVG element: '+tag)
        e.tag=tag
        for name,value in e.attrib.items():
            if name not in attrs or re.search(r'url\s*\(|javascript:|https?:|data:',value,re.I):
                raise ValueError('Unsupported SVG attribute: '+name)
    root.set('xmlns','http://www.w3.org/2000/svg')
    return ET.tostring(root,encoding='unicode')

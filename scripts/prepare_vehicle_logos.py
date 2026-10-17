"""Strict sanitizer for locally supplied, reviewed make-logo SVG files."""
import xml.etree.ElementTree as ET
import re

def sanitize_svg(svg):
    if len(svg)>200000 or re.search(r'<!DOCTYPE|<!ENTITY',svg,re.I):
        raise ValueError('Unsupported SVG document')
    root=ET.fromstring(svg)
    allowed={'svg','path','g','title','desc','circle','ellipse','rect','polygon','polyline','line','defs','linearGradient','radialGradient','stop','clipPath'}
    attrs={'viewBox','width','height','d','fill','fill-rule','clip-rule','transform','cx','cy','r','rx','ry','x','y','x1','y1','x2','y2','points','stroke','stroke-width','stroke-linecap','stroke-linejoin','role','opacity','id','preserveAspectRatio','gradientUnits','gradientTransform','spreadMethod','fx','fy','offset','stop-color','stop-opacity','fill-opacity','stroke-opacity','clip-path','clipPathUnits','stroke-miterlimit','stroke-dasharray','stroke-dashoffset','vector-effect','display'}
    if root.tag.rsplit('}',1)[-1]!='svg' or not root.get('viewBox'):
        raise ValueError('SVG requires a viewBox')
    for e in root.iter():
        tag=e.tag.rsplit('}',1)[-1]
        if tag not in allowed: raise ValueError('Unsupported SVG element: '+tag)
        e.tag=tag
        for name,value in list(e.attrib.items()):
            if name in {'version','{http://www.w3.org/XML/1998/namespace}space','data-name'}:
                del e.attrib[name]
                continue
            if name == 'style':
                for declaration in value.split(';'):
                    if not declaration.strip(): continue
                    prop, separator, val = declaration.partition(':')
                    if not separator or prop.strip() not in attrs:
                        raise ValueError('Unsupported SVG style')
                    e.set(prop.strip(),val.strip())
                del e.attrib[name]
        for name,value in e.attrib.items():
            local_reference = re.fullmatch(r'url\(#[A-Za-z_][\w.-]*\)',value)
            if name not in attrs or (re.search(r'url\s*\(|javascript:|https?:|data:',value,re.I) and not local_reference):
                raise ValueError('Unsupported SVG attribute: '+name)
    root.set('xmlns','http://www.w3.org/2000/svg')
    return ET.tostring(root,encoding='unicode')

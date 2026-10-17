"""Developer-only PNG tracing. Requires Pillow and vtracer; never runs in HA."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

if __package__:
    from .prepare_vehicle_logos import sanitize_svg
else:
    from prepare_vehicle_logos import sanitize_svg


def vectorize(input_path, output_path, source_url, monochrome=False, polygon=False,
              alpha_mask=False, max_bytes=80000):
    """Write paths, not an embedded bitmap; manual visual review is still required."""
    from PIL import Image
    import vtracer
    source=Path(input_path)
    image=Image.open(source).convert('RGBA')
    image.thumbnail((1200,1200))
    if monochrome:
        pixels=[]
        data=image.get_flattened_data() if hasattr(image,'get_flattened_data') else image.getdata()
        for r,g,b,a in data:
            foreground=a>128 and (alpha_mask or (r+g+b)/3<160)
            pixels.append((0,0,0,255) if foreground else (255,255,255,255))
        image.putdata(pixels)
    with tempfile.TemporaryDirectory() as folder:
        png=Path(folder)/'prepared.png';svg_path=Path(folder)/'trace.svg'
        image.save(png)
        vtracer.convert_image_to_svg_py(str(png),str(svg_path),
            colormode='binary' if monochrome else 'color',
            mode='polygon' if polygon else 'spline',
            filter_speckle=0 if polygon else 2, color_precision=6,
            layer_difference=16, corner_threshold=90 if polygon else 60,
            length_threshold=3.5,path_precision=3)
        root=ET.fromstring(svg_path.read_text(encoding='utf-8'))
        root.set('viewBox',f'0 0 {image.width} {image.height}')
        svg=sanitize_svg(ET.tostring(root,encoding='unicode'))
    if len(svg.encode())>max_bytes:
        raise ValueError('Trace exceeds size budget; retain PNG or find an original vector')
    output=Path(output_path);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(svg,encoding='utf-8')
    return {'origin':'raster_trace','source_url':source_url,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'sha256':hashlib.sha256(svg.encode()).hexdigest(),
            'tracer':'vtracer','mode':'polygon' if polygon else 'spline',
            'monochrome':monochrome,'requires_visual_review':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--source-url',required=True)
    parser.add_argument('--monochrome',action='store_true')
    parser.add_argument('--polygon',action='store_true')
    parser.add_argument('--alpha-mask',action='store_true',help='Trace a white logo on transparency')
    args=parser.parse_args()
    if args.input.resolve()==args.output.resolve():parser.error('Keep the original image')
    print(json.dumps(vectorize(args.input,args.output,args.source_url,
        args.monochrome,args.polygon,args.alpha_mask),indent=2))


if __name__=='__main__':main()

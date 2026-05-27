#!/usr/bin/python3
import sys
import re
from lxml import etree
import os
import subprocess
import tempfile

def parse_depth(depth_str):
    """Parses a depth string like '5.08cm' into a float, ignoring the unit."""
    if not depth_str:
        return 0.0
    match = re.match(r"([0-9.]+)", depth_str)
    if match:
        return float(match.group(1))
    return 0.0

def is_black(fill_str):
    """Checks if a fill color is black."""
    if not fill_str:
        return False
    f = fill_str.lower().replace(" ", "")
    return f in ["rgb(0,0,0)", "#000000", "#000", "black"]

def run_inkscape_union(elements, namespaces):
    """Uses Inkscape to perform a geometric union on a list of elements."""
    if not elements:
        return []
    
    valid_elements = [e for e in elements if e.get('d') or e.tag.endswith(('path', 'rect', 'circle'))]
    if not valid_elements:
        return []

    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_in:
        tmp_in_name = tmp_in.name
        # Use a large viewBox to prevent clipping
        tmp_root = etree.Element("svg", nsmap=namespaces)
        tmp_root.set("viewBox", "-1000 -1000 2000 2000")
        for elem in valid_elements:
            tmp_root.append(etree.fromstring(etree.tostring(elem)))
        tmp_in.write(etree.tostring(tmp_root, xml_declaration=True, encoding='utf-8'))

    tmp_out_name = tmp_in_name.replace(".svg", "_out.svg")
    
    try:
        # Actions: select-all; apply transforms (flatten); convert to path; union; export plain svg
        cmd = [
            "inkscape", tmp_in_name,
            "--actions", "select-all;selection-apply-transform;object-to-path;select-all;path-union;export-plain-svg;export-filename:" + tmp_out_name + ";export-do",
            "--batch-process"
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        if os.path.exists(tmp_out_name):
            with open(tmp_out_name, 'rb') as f:
                out_tree = etree.parse(f)
            svg_ns = "http://www.w3.org/2000/svg"
            return out_tree.getroot().xpath(".//svg:path", namespaces={'svg': svg_ns})
        else:
            return []
    finally:
        if os.path.exists(tmp_in_name): os.remove(tmp_in_name)
        if os.path.exists(tmp_out_name): os.remove(tmp_out_name)

def process_svg(input_file):
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found.")
        return

    with open(input_file, 'rb') as f:
        tree = etree.parse(f)
    
    root = tree.getroot()
    namespaces = {k: v for k, v in root.nsmap.items() if k is not None}
    shaper_ns = namespaces.get('shaper', 'http://www.shapertools.com/namespaces/shaper')
    namespaces['shaper'] = shaper_ns
    cut_depth_attr = f"{{{shaper_ns}}}cutDepth"

    # Collect elements and their depths
    elements = []
    depth_map = {} # val -> original depth string
    for elem in root.xpath(".//*[@shaper:cutDepth]", namespaces=namespaces):
        d_str = elem.get(cut_depth_attr)
        val = parse_depth(d_str)
        elements.append((val, elem))
        depth_map[val] = d_str
    
    unique_depths = sorted(list(depth_map.keys()))
    input_base = os.path.splitext(input_file)[0]
    
    for target_val in unique_depths:
        target_str = depth_map[target_val]
        # Create output root with original attributes (viewBox, etc.)
        new_root = etree.Element(root.tag, nsmap=root.nsmap, attrib=root.attrib)
        
        black_elements = []
        white_elements = []
        
        for val, elem in elements:
            if val >= target_val:
                if is_black(elem.get('fill', '')):
                    black_elements.append(elem)
                else:
                    white_elements.append(elem)
        
        print(f"Processing depth {target_str}...")

        # 1. Merge and add black elements first
        if black_elements:
            merged_black = run_inkscape_union(black_elements, root.nsmap)
            for p in merged_black:
                p.set('fill', "rgb(0,0,0)")
                p.set(cut_depth_attr, target_str)
                new_root.append(p)
                
        # 2. Merge and add white elements on top
        if white_elements:
            merged_white = run_inkscape_union(white_elements, root.nsmap)
            for p in merged_white:
                # Add the specific style requested by the user
                p.set('style', "fill:#ffffff;fill-opacity:1")
                # Remove individual fill attribute if Inkscape added one
                p.attrib.pop('fill', None)
                p.set(cut_depth_attr, target_str)
                new_root.append(p)

        output_depth_str = target_str.replace('.', '-')
        output_filename = f"{input_base}_{output_depth_str}.svg"
        with open(output_filename, 'wb') as f:
            f.write(etree.tostring(new_root, pretty_print=True, xml_declaration=True, encoding='utf-8'))
        print(f"Generated {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_svg.py <input.svg>")
    else:
        process_svg(sys.argv[1])

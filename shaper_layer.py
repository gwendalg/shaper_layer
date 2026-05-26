#!/usr/bin/python3
import sys
import re
from lxml import etree
import os

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

def process_svg(input_file):
    """
    Processes an SVG file to group shapes by 'shaper:cutDepth'.
    For each unique depth, it creates a new SVG containing all shapes that are 
    at that depth or deeper, setting their cutDepth to the target depth 
    and merging paths with identical attributes.
    """
    with open(input_file, 'rb') as f:
        tree = etree.parse(f)
    
    root = tree.getroot()
    # Filter out empty namespace prefix which causes XPath errors
    namespaces = {k: v for k, v in root.nsmap.items() if k is not None}
    shaper_ns = namespaces.get('shaper', 'http://www.shapertools.com/namespaces/shaper')
    namespaces['shaper'] = shaper_ns
    cut_depth_attr = f"{{{shaper_ns}}}cutDepth"

    # Identify all elements with a cutDepth attribute
    elements = []
    depth_map = {} # numeric_val -> original_string
    
    for elem in root.xpath(".//*[@shaper:cutDepth]", namespaces=namespaces):
        depth_str = elem.get(cut_depth_attr)
        val = parse_depth(depth_str)
        elements.append((val, elem))
        depth_map[val] = depth_str
    
    # Process depths from shallowest to deepest
    unique_depth_vals = sorted(list(depth_map.keys()))
    print(f"Processing depths: {[depth_map[v] for v in unique_depth_vals]}")

    input_base = os.path.splitext(input_file)[0]
    # Handle the default SVG namespace
    svg_ns = root.tag.split('}')[0].strip('{') if '}' in root.tag else 'http://www.w3.org/2000/svg'
    path_tag = f"{{{svg_ns}}}path"

    for target_val in unique_depth_vals:
        target_str = depth_map[target_val]
        # Create a new SVG document with the same properties as the original
        new_root = etree.Element(root.tag, nsmap=root.nsmap, attrib=root.attrib)
        
        # Group paths by attributes to merge them into compound paths
        attribute_groups = {}
        
        for val, elem in elements:
            # Include shapes that are at this depth or deeper
            if val >= target_val:
                # Copy attributes but exclude the path data and the cutDepth
                attrs = dict(elem.attrib)
                
                # Fill logic: set to white unless it's black
                current_fill = attrs.get('fill', '')
                if not is_black(current_fill):
                    attrs['fill'] = "rgb(255, 255, 255)"
                    # Remove stroke and fill-rule attributes for white paths to indicate through cuts
                    attrs.pop('stroke', None)
                    attrs.pop('stroke-width', None)
                    attrs.pop('fill-rule', None)
                
                path_data = attrs.pop('d', None)
                attrs.pop(cut_depth_attr, None)
                
                # Create a key based on style/transform attributes
                group_key = tuple(sorted(attrs.items()))
                
                if path_data:
                    if group_key not in attribute_groups:
                        attribute_groups[group_key] = {'attrs': attrs, 'd_list': []}
                    attribute_groups[group_key]['d_list'].append(path_data)
                else:
                    # For non-path elements (rect, circle, etc.), keep them as separate elements
                    new_elem = etree.fromstring(etree.tostring(elem))
                    new_elem.set(cut_depth_attr, target_str)
                    if not is_black(new_elem.get('fill')):
                        new_elem.set('fill', "rgb(255, 255, 255)")
                        new_elem.attrib.pop('stroke', None)
                        new_elem.attrib.pop('stroke-width', None)
                        new_elem.attrib.pop('fill-rule', None)
                    new_root.append(new_elem)
        
        # Add the merged paths to the new document
        for group_key, data in attribute_groups.items():
            if not data['d_list']:
                continue
            
            # Combine all path data strings into a single compound path
            merged_d = " ".join(data['d_list'])
            merged_attrs = data['attrs']
            merged_attrs['d'] = merged_d
            # Ensure the cutDepth is uniform for all elements in this file
            merged_attrs[cut_depth_attr] = target_str
            
            new_path = etree.Element(path_tag, attrib=merged_attrs)
            new_root.append(new_path)
        
        # Save the result in the orignal directory.
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

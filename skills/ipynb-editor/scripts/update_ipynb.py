import json
import sys
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Update a Jupyter Notebook safely.")
    parser.add_argument("--file", required=True, help="Path to the .ipynb file")
    
    # We still keep these for backward compatibility
    parser.add_argument("--cell", type=int, help="Zero-based index of the cell to update")
    parser.add_argument("--source", help="Path to a text file containing the new source code for the cell")
    
    args = parser.parse_args()
    
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            nb = json.load(f)
            
        cells = nb.get('cells', [])
        
        # Mode 1: Find and Replace via Environment Variables
        find_str = os.environ.get('FIND')
        replace_str = os.environ.get('REPLACE')
        
        if find_str is not None and replace_str is not None:
            updated_count = 0
            for cell in cells:
                if 'source' in cell:
                    # 'source' can be a string or a list of strings
                    if isinstance(cell['source'], list):
                        source_str = "".join(cell['source'])
                    else:
                        source_str = cell['source']
                        
                    if find_str in source_str:
                        new_source_str = source_str.replace(find_str, replace_str)
                        # Keep standard format of list of strings with newlines
                        cell['source'] = new_source_str.splitlines(True)
                        if 'outputs' in cell:
                            cell['outputs'] = []
                        if 'execution_count' in cell:
                            cell['execution_count'] = None
                        updated_count += 1
                        
            if updated_count == 0:
                print(f"Error: Could not find the text specified in FIND inside any cell.", file=sys.stderr)
                sys.exit(1)
            print(f"Successfully replaced text in {updated_count} cell(s) in {args.file}")
            
        # Mode 2: Replace whole cell from file
        elif args.cell is not None and args.source is not None:
            if args.cell < 0 or args.cell >= len(cells):
                print(f"Error: Cell index {args.cell} is out of bounds (0 to {len(cells)-1}).", file=sys.stderr)
                sys.exit(1)
                
            with open(args.source, 'r', encoding='utf-8') as f:
                new_source_text = f.read()
                
            cells[args.cell]['source'] = new_source_text.splitlines(True)
            if 'outputs' in cells[args.cell]:
                cells[args.cell]['outputs'] = []
            if 'execution_count' in cells[args.cell]:
                cells[args.cell]['execution_count'] = None
                
            print(f"Successfully updated cell {args.cell} in {args.file} from {args.source}")
        else:
            print("Error: Must provide either FIND and REPLACE env vars, or --cell and --source args.", file=sys.stderr)
            sys.exit(1)
            
        with open(args.file, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

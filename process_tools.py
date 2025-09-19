#!/usr/bin/env python3
"""
Process tools directory for docstring generation.
"""

import ast
import re
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_description_from_name(name: str) -> str:
    """Generate a description based on a function or class name."""
    words = re.sub(r'([A-Z])', r' \1', name).replace('_', ' ').strip().split()
    
    # Tool-specific patterns
    if 'tool' in name.lower():
        if name.startswith('get_'):
            return f"Get {' '.join(words[1:]).lower()}."
        elif name.startswith('create_'):
            return f"Create {' '.join(words[1:]).lower()}."
        elif name.startswith('list_'):
            return f"List {' '.join(words[1:]).lower()}."
        elif name.startswith('search_'):
            return f"Search {' '.join(words[1:]).lower()}."
        elif name.startswith('update_'):
            return f"Update {' '.join(words[1:]).lower()}."
        elif name.startswith('delete_'):
            return f"Delete {' '.join(words[1:]).lower()}."
        else:
            return f"Tool function for {' '.join(words).lower()}."
    
    # Standard patterns
    if name.startswith('get_'):
        return f"Get {' '.join(words[1:]).lower()}."
    elif name.startswith('set_'):
        return f"Set {' '.join(words[1:]).lower()}."
    elif name.startswith('create_'):
        return f"Create {' '.join(words[1:]).lower()}."
    elif name.startswith('delete_'):
        return f"Delete {' '.join(words[1:]).lower()}."
    elif name.startswith('update_'):
        return f"Update {' '.join(words[1:]).lower()}."
    elif name.startswith('list_'):
        return f"List {' '.join(words[1:]).lower()}."
    elif name.startswith('search_'):
        return f"Search {' '.join(words[1:]).lower()}."
    elif name.startswith('find_'):
        return f"Find {' '.join(words[1:]).lower()}."
    elif name.startswith('add_'):
        return f"Add {' '.join(words[1:]).lower()}."
    elif name.startswith('remove_'):
        return f"Remove {' '.join(words[1:]).lower()}."
    elif name.startswith('process_'):
        return f"Process {' '.join(words[1:]).lower()}."
    elif name.startswith('handle_'):
        return f"Handle {' '.join(words[1:]).lower()}."
    elif name.startswith('validate_'):
        return f"Validate {' '.join(words[1:]).lower()}."
    elif name.startswith('parse_'):
        return f"Parse {' '.join(words[1:]).lower()}."
    elif name.startswith('format_'):
        return f"Format {' '.join(words[1:]).lower()}."
    elif name.startswith('render_'):
        return f"Render {' '.join(words[1:]).lower()}."
    elif name.startswith('build_'):
        return f"Build {' '.join(words[1:]).lower()}."
    elif name.startswith('execute_'):
        return f"Execute {' '.join(words[1:]).lower()}."
    elif name.startswith('run_'):
        return f"Run {' '.join(words[1:]).lower()}."
    elif name.startswith('start_'):
        return f"Start {' '.join(words[1:]).lower()}."
    elif name.startswith('stop_'):
        return f"Stop {' '.join(words[1:]).lower()}."
    elif name.startswith('init'):
        return f"Initialize {' '.join(words[1:]).lower() if len(words) > 1 else 'the instance'}."
    elif name.startswith('setup'):
        return f"Set up {' '.join(words[1:]).lower()}."
    elif name.startswith('cleanup'):
        return f"Clean up {' '.join(words[1:]).lower()}."
    else:
        # Generic description
        words = [w.lower() for w in words]
        if words:
            words[0] = words[0].capitalize()
            return f"{' '.join(words)}."
        else:
            return "TODO: Add description."

def generate_function_docstring(name: str, args: list, has_return: bool, indent: int) -> str:
    """Generate a Google-style docstring for a function."""
    base_indent = ' ' * indent
    description = generate_description_from_name(name)
    
    docstring_parts = [f'{base_indent}"""{description}']
    
    # Add Args section if function has parameters
    if args:
        filtered_args = [arg for arg in args if arg not in ['self', 'cls']]
        if filtered_args:
            docstring_parts.append(f'{base_indent}')
            docstring_parts.append(f'{base_indent}Args:')
            for arg in filtered_args:
                docstring_parts.append(f'{base_indent}    {arg}: TODO: Add description')
    
    # Add Returns section if function has return annotation
    if has_return:
        if args and len([arg for arg in args if arg not in ['self', 'cls']]) > 0:
            docstring_parts.append(f'{base_indent}    ')
        else:
            docstring_parts.append(f'{base_indent}')
        docstring_parts.append(f'{base_indent}Returns:')
        docstring_parts.append(f'{base_indent}    TODO: Add return description')
    
    docstring_parts.append(f'{base_indent}"""')
    return '\n'.join(docstring_parts)

def process_file(file_path: str) -> bool:
    """Process a single file to add missing docstrings."""
    logger.info(f"Processing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        tree = ast.parse(content)
        
        # Find functions without docstrings
        missing_functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                has_docstring = ast.get_docstring(node) is not None
                if not has_docstring and not node.name.startswith('_'):
                    args = [arg.arg for arg in node.args.args]
                    missing_functions.append({
                        'name': node.name,
                        'lineno': node.lineno,
                        'args': args,
                        'has_return': node.returns is not None
                    })
        
        if not missing_functions:
            logger.info("No missing docstrings found")
            return False
        
        logger.info(f"Found {len(missing_functions)} functions missing docstrings")
        
        # Sort by line number in reverse order
        missing_functions.sort(key=lambda x: x['lineno'], reverse=True)
        
        modified = False
        for func in missing_functions:
            line_num = func['lineno'] - 1
            
            if line_num >= len(lines):
                continue
            
            # Get indentation
            def_line = lines[line_num]
            indent = len(def_line) - len(def_line.lstrip())
            
            # Find the colon
            colon_line = line_num
            while colon_line < len(lines) and ':' not in lines[colon_line]:
                colon_line += 1
            
            if colon_line >= len(lines):
                continue
            
            # Generate docstring
            docstring = generate_function_docstring(
                func['name'], 
                func['args'], 
                func['has_return'],
                indent + 4
            )
            
            # Insert docstring
            docstring_lines = docstring.split('\n')
            for i, ds_line in enumerate(docstring_lines):
                lines.insert(colon_line + 1 + i, ds_line)
            
            modified = True
            logger.info(f"Added docstring to function '{func['name']}'")
        
        if modified:
            # Create backup
            backup_path = f"{file_path}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Write updated file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
                
            logger.info(f"Updated {file_path} (backup: {backup_path})")
        
        return modified
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False

def main():
    """Process tools files for docstring generation."""
    
    # Key tool files to process
    target_files = [
        "tools/notes_tool.py",
        "tools/projects_tool.py", 
        "tools/basic_tools.py",
        "tools/file_search_tool.py"
    ]
    
    logger.info("Starting docstring generation for tools...")
    
    processed_count = 0
    total_functions = 0
    
    for file_path in target_files:
        if Path(file_path).exists():
            logger.info(f"\n--- Processing {file_path} ---")
            
            # Count functions before processing
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
                
                file_functions = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if not ast.get_docstring(node) and not node.name.startswith('_'):
                            file_functions += 1
                
                total_functions += file_functions
                logger.info(f"Expected: {file_functions} functions")
                
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
            
            if process_file(file_path):
                processed_count += 1
        else:
            logger.warning(f"File not found: {file_path}")
    
    logger.info(f"\nProcessing complete!")
    logger.info(f"Files modified: {processed_count}")
    logger.info(f"Expected functions documented: {total_functions}")

if __name__ == "__main__":
    main()
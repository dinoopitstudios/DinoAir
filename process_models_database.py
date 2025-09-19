#!/usr/bin/env python3
"""
Extended docstring generator for models and database modules.
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
    
    # Function patterns
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
    elif name.startswith('save_'):
        return f"Save {' '.join(words[1:]).lower()}."
    elif name.startswith('load_'):
        return f"Load {' '.join(words[1:]).lower()}."
    elif name.startswith('find_'):
        return f"Find {' '.join(words[1:]).lower()}."
    elif name.startswith('search_'):
        return f"Search {' '.join(words[1:]).lower()}."
    elif name.startswith('validate_'):
        return f"Validate {' '.join(words[1:]).lower()}."
    elif name.startswith('process_'):
        return f"Process {' '.join(words[1:]).lower()}."
    elif name.startswith('handle_'):
        return f"Handle {' '.join(words[1:]).lower()}."
    elif name.startswith('init'):
        return f"Initialize {' '.join(words[1:]).lower() if len(words) > 1 else 'the instance'}."
    elif name.startswith('build'):
        return f"Build {' '.join(words[1:]).lower()}."
    elif name.startswith('parse'):
        return f"Parse {' '.join(words[1:]).lower()}."
    elif name.startswith('serialize'):
        return f"Serialize {' '.join(words[1:]).lower()}."
    elif name.startswith('deserialize'):
        return f"Deserialize {' '.join(words[1:]).lower()}."
    elif name.startswith('to_'):
        return f"Convert to {' '.join(words[1:]).lower()}."
    elif name.startswith('from_'):
        return f"Create from {' '.join(words[1:]).lower()}."
    elif name.startswith('is_'):
        return f"Check if {' '.join(words[1:]).lower()}."
    elif name.startswith('has_'):
        return f"Check if has {' '.join(words[1:]).lower()}."
    elif name.startswith('can_'):
        return f"Check if can {' '.join(words[1:]).lower()}."
    else:
        # Generic description
        words = [w.lower() for w in words]
        if words:
            words[0] = words[0].capitalize()
            return f"{' '.join(words)}."
        else:
            return "TODO: Add description."

def generate_class_docstring(name: str, indent: int) -> str:
    """Generate a Google-style docstring for a class."""
    base_indent = ' ' * indent
    
    # Special handling for common class patterns
    if name.endswith('Database') or name.endswith('DB'):
        description = f"{name} class for database operations."
    elif name.endswith('Service'):
        description = f"{name} class for service operations."
    elif name.endswith('Manager'):
        description = f"{name} class for management operations."
    elif name.endswith('Handler'):
        description = f"{name} class for handling operations."
    elif name.endswith('Config'):
        description = f"{name} configuration class."
    elif name.endswith('Model'):
        description = f"{name} data model class."
    elif name.endswith('Exception'):
        description = f"{name} exception class."
    elif name.endswith('Error'):
        description = f"{name} error class."
    else:
        description = generate_description_from_name(name)
    
    return f'{base_indent}"""{description}"""'

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
        
        # Find missing docstrings
        missing_items = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                has_docstring = ast.get_docstring(node) is not None
                if not has_docstring:
                    missing_items.append({
                        'type': 'class',
                        'name': node.name,
                        'lineno': node.lineno
                    })
                    
            elif isinstance(node, ast.FunctionDef):
                has_docstring = ast.get_docstring(node) is not None
                if not has_docstring and not node.name.startswith('_'):
                    args = [arg.arg for arg in node.args.args]
                    missing_items.append({
                        'type': 'function',
                        'name': node.name,
                        'lineno': node.lineno,
                        'args': args,
                        'has_return': node.returns is not None
                    })
        
        if not missing_items:
            logger.info("No missing docstrings found")
            return False
        
        logger.info(f"Found {len(missing_items)} items missing docstrings")
        
        # Sort by line number in reverse order
        missing_items.sort(key=lambda x: x['lineno'], reverse=True)
        
        modified = False
        for item in missing_items:
            line_num = item['lineno'] - 1
            
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
            
            # Generate appropriate docstring
            if item['type'] == 'function':
                docstring = generate_function_docstring(
                    item['name'], 
                    item['args'], 
                    item['has_return'],
                    indent + 4
                )
            else:  # class
                docstring = generate_class_docstring(
                    item['name'],
                    indent + 4
                )
            
            # Insert docstring
            docstring_lines = docstring.split('\n')
            for i, ds_line in enumerate(docstring_lines):
                lines.insert(colon_line + 1 + i, ds_line)
            
            modified = True
            logger.info(f"Added docstring to {item['type']} '{item['name']}'")
        
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
    """Process models and database files for docstring generation."""
    
    # Key files to process
    target_files = [
        # Models
        "models/note_v2.py",
        "models/calendar_event.py", 
        "models/calendar_event_v2.py",
        "models/project.py",
        "models/base.py",
        
        # Database
        "database/notes_service.py",
        "database/notes_repository.py",
        "database/notes_validator.py",
        "database/projects_db.py",
        "database/appointments_db.py",
        "database/artifacts_db.py",
        "database/timers_db.py",
        "database/file_search_db.py",
        "database/factory.py",
        "database/interfaces.py",
        "database/resilient_db.py"
    ]
    
    logger.info("Starting extended docstring generation for models and database...")
    
    processed_count = 0
    total_functions = 0
    total_classes = 0
    
    for file_path in target_files:
        if Path(file_path).exists():
            logger.info(f"\n--- Processing {file_path} ---")
            
            # Count items before processing
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
                
                file_functions = 0
                file_classes = 0
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if not ast.get_docstring(node):
                            file_classes += 1
                    elif isinstance(node, ast.FunctionDef):
                        if not ast.get_docstring(node) and not node.name.startswith('_'):
                            file_functions += 1
                
                total_functions += file_functions
                total_classes += file_classes
                
                logger.info(f"Expected: {file_functions} functions, {file_classes} classes")
                
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
            
            if process_file(file_path):
                processed_count += 1
        else:
            logger.warning(f"File not found: {file_path}")
    
    logger.info(f"\nProcessing complete!")
    logger.info(f"Files modified: {processed_count}")
    logger.info(f"Expected functions documented: {total_functions}")
    logger.info(f"Expected classes documented: {total_classes}")

if __name__ == "__main__":
    main()
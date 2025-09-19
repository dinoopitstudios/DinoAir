#!/usr/bin/env python3
"""
Comprehensive docstring generator for DinoAir project.

This script systematically adds Google-style docstrings to Python files
that are missing documentation for functions and classes.
"""

import ast
import re
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocstringGenerator:
    """Generate docstrings for Python functions and classes."""
    
    def __init__(self):
        """Initialize the docstring generator."""
        self.processed_files = 0
        self.processed_functions = 0
        self.processed_classes = 0
        
    def generate_description_from_name(self, name: str) -> str:
        """
        Generate a description based on a function or class name.
        
        Args:
            name: The function or class name
            
        Returns:
            Generated description string
        """
        # Convert camelCase and snake_case to readable text
        words = re.sub(r'([A-Z])', r' \1', name).replace('_', ' ').strip().split()
        
        # Common patterns for functions
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
        elif name.startswith('is_'):
            return f"Check if {' '.join(words[1:]).lower()}."
        elif name.startswith('has_'):
            return f"Check if has {' '.join(words[1:]).lower()}."
        elif name.startswith('can_'):
            return f"Check if can {' '.join(words[1:]).lower()}."
        elif name.startswith('should_'):
            return f"Check if should {' '.join(words[1:]).lower()}."
        elif name.startswith('load_'):
            return f"Load {' '.join(words[1:]).lower()}."
        elif name.startswith('save_'):
            return f"Save {' '.join(words[1:]).lower()}."
        elif name.startswith('parse_'):
            return f"Parse {' '.join(words[1:]).lower()}."
        elif name.startswith('validate_'):
            return f"Validate {' '.join(words[1:]).lower()}."
        elif name.startswith('process_'):
            return f"Process {' '.join(words[1:]).lower()}."
        elif name.startswith('handle_'):
            return f"Handle {' '.join(words[1:]).lower()}."
        elif name.startswith('init'):
            return f"Initialize {' '.join(words[1:]).lower()}."
        elif name.startswith('setup'):
            return f"Set up {' '.join(words[1:]).lower()}."
        elif name.startswith('cleanup'):
            return f"Clean up {' '.join(words[1:]).lower()}."
        elif name.startswith('run'):
            return f"Run {' '.join(words[1:]).lower()}."
        elif name.startswith('execute'):
            return f"Execute {' '.join(words[1:]).lower()}."
        elif name.startswith('build'):
            return f"Build {' '.join(words[1:]).lower()}."
        elif name.startswith('connect'):
            return f"Connect {' '.join(words[1:]).lower()}."
        elif name.startswith('disconnect'):
            return f"Disconnect {' '.join(words[1:]).lower()}."
        else:
            # Capitalize first word and add period
            words = [w.lower() for w in words]
            if words:
                words[0] = words[0].capitalize()
                return f"{' '.join(words)}."
            else:
                return "TODO: Add description."

    def generate_function_docstring(self, name: str, args: List[str], 
                                  has_return: bool = False, indent: int = 4) -> str:
        """
        Generate a Google-style docstring for a function.
        
        Args:
            name: Function name
            args: List of argument names
            has_return: Whether function has return annotation
            indent: Number of spaces for indentation
            
        Returns:
            Generated docstring with proper indentation
        """
        base_indent = ' ' * indent
        description = self.generate_description_from_name(name)
        
        docstring_parts = [f'{base_indent}"""{description}']
        
        # Add Args section if function has parameters
        if args and len(args) > 0:
            # Filter out 'self' and 'cls'
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

    def generate_class_docstring(self, name: str, indent: int = 4) -> str:
        """
        Generate a Google-style docstring for a class.
        
        Args:
            name: Class name
            indent: Number of spaces for indentation
            
        Returns:
            Generated docstring with proper indentation
        """
        base_indent = ' ' * indent
        description = self.generate_description_from_name(name)
        
        return f'{base_indent}"""{description}"""'

    def find_missing_docstrings(self, file_path: str) -> Dict[str, Any]:
        """
        Find functions and classes missing docstrings in a file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary containing missing docstring information
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Check module-level docstring
            has_module_docstring = (isinstance(tree.body[0], ast.Expr) and 
                                  isinstance(tree.body[0].value, ast.Constant) and 
                                  isinstance(tree.body[0].value.value, str)) if tree.body else False
            
            # Find classes and functions without docstrings
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
            
            return {
                'file': file_path,
                'module_docstring': has_module_docstring,
                'missing_items': missing_items
            }
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return {'file': file_path, 'module_docstring': True, 'missing_items': []}

    def add_docstrings_to_file(self, file_info: Dict[str, Any]) -> bool:
        """
        Add docstrings to a file.
        
        Args:
            file_info: Dictionary containing file and missing docstring info
            
        Returns:
            True if file was modified, False otherwise
        """
        file_path = file_info['file']
        missing_items = file_info['missing_items']
        
        if not missing_items:
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            
            # Sort by line number in descending order to avoid line shifts
            missing_items.sort(key=lambda x: x['lineno'], reverse=True)
            
            for item in missing_items:
                line_num = item['lineno'] - 1  # Convert to 0-based index
                
                if line_num >= len(lines):
                    continue
                    
                # Get the definition line and find its indentation
                def_line = lines[line_num]
                indent = len(def_line) - len(def_line.lstrip())
                
                # Find the end of the definition (after colon)
                colon_line = line_num
                while colon_line < len(lines) and ':' not in lines[colon_line]:
                    colon_line += 1
                
                if colon_line >= len(lines):
                    continue
                
                # Generate appropriate docstring
                if item['type'] == 'function':
                    docstring = self.generate_function_docstring(
                        item['name'], 
                        item['args'], 
                        item.get('has_return', False),
                        indent + 4  # Add extra indentation for function body
                    )
                    self.processed_functions += 1
                else:  # class
                    docstring = self.generate_class_docstring(
                        item['name'], 
                        indent + 4  # Add extra indentation for class body
                    )
                    self.processed_classes += 1
                
                # Insert docstring after the definition line
                docstring_lines = [line + '\n' for line in docstring.split('\n')]
                for i, ds_line in enumerate(docstring_lines):
                    lines.insert(colon_line + 1 + i, ds_line)
                
                modified = True
                logger.info(f"Added docstring to {item['type']} '{item['name']}' at line {item['lineno']}")
            
            if modified:
                # Create backup
                backup_path = f"{file_path}.backup"
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write updated file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                self.processed_files += 1
                logger.info(f"Updated {file_path} (backup: {backup_path})")
                
            return modified
            
        except Exception as e:
            logger.error(f"Error updating {file_path}: {e}")
            return False

    def process_files(self, file_paths: List[str], max_files: int = None) -> None:
        """
        Process multiple files to add docstrings.
        
        Args:
            file_paths: List of file paths to process
            max_files: Maximum number of files to process (None for all)
        """
        files_to_process = file_paths[:max_files] if max_files else file_paths
        
        logger.info(f"Processing {len(files_to_process)} files...")
        
        for file_path in files_to_process:
            logger.info(f"Processing: {file_path}")
            file_info = self.find_missing_docstrings(file_path)
            
            if file_info['missing_items']:
                logger.info(f"Found {len(file_info['missing_items'])} items missing docstrings")
                self.add_docstrings_to_file(file_info)
            else:
                logger.info("No missing docstrings found")

def find_python_files(directories: List[str]) -> List[str]:
    """
    Find all Python files in specified directories.
    
    Args:
        directories: List of directory paths to scan
        
    Returns:
        List of Python file paths
    """
    python_files = []
    
    for directory in directories:
        if not os.path.exists(directory):
            logger.warning(f"Directory {directory} does not exist, skipping...")
            continue
            
        for py_file in Path(directory).rglob('*.py'):
            if py_file.name != '__init__.py':
                python_files.append(str(py_file))
    
    return python_files

def main():
    """Main function to orchestrate docstring generation."""
    
    # Target directories
    target_directories = ['utils', 'models', 'database', 'tools']
    
    logger.info("Starting comprehensive docstring generation for DinoAir project...")
    
    # Find all Python files
    python_files = find_python_files(target_directories)
    logger.info(f"Found {len(python_files)} Python files to analyze")
    
    # Create generator instance
    generator = DocstringGenerator()
    
    # Ask for confirmation
    print(f"\nWould you like to add docstrings to up to {len(python_files)} Python files?")
    print("This will create .backup files and add Google-style docstrings to functions and classes.")
    
    # Option to limit number of files for testing
    max_files = input(f"Enter max files to process (press Enter for all): ").strip()
    max_files = int(max_files) if max_files.isdigit() else None
    
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        logger.info("Operation cancelled by user")
        return
    
    # Process files
    generator.process_files(python_files, max_files)
    
    logger.info(f"Processing complete!")
    logger.info(f"Files modified: {generator.processed_files}")
    logger.info(f"Functions documented: {generator.processed_functions}")
    logger.info(f"Classes documented: {generator.processed_classes}")

if __name__ == "__main__":
    main()
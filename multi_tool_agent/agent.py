from google.adk.agents import Agent
import os
import datetime
import re
import fnmatch
from typing import List, Dict, Optional, Tuple, Union
import json
from pathlib import Path
import mimetypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the root directory for file searches from environment variable
# Default to user's home directory if not specified
ROOT_SEARCH_DIR = os.environ.get("ROOT_SEARCH_DIR", os.path.expanduser("~"))
# Maximum depth for directory traversal when listing areas/subareas
MAX_DEPTH = int(os.environ.get("MAX_DEPTH", "3"))
# Maximum number of results to return
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "50"))
# Extension to include in content searching (plain text files)
SEARCHABLE_EXTENSIONS = os.environ.get("SEARCHABLE_EXTENSIONS", ".txt,.md,.csv,.json,.py,.html,.xml,.yaml,.yml").split(",")

def list_areas(depth: int = 1) -> List[Dict[str, str]]:
    """Lists all areas (top-level directories) in the root search directory.
    
    Args:
        depth (int): How many levels of directories to traverse. Default is 1.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing area names and paths.
    """
    areas = []
    for root, dirs, _ in os.walk(ROOT_SEARCH_DIR):
        # Calculate current depth
        current_depth = root.count(os.sep) - ROOT_SEARCH_DIR.count(os.sep)
        if current_depth >= depth:
            continue
            
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            # Skip hidden directories and system folders
            if dir_name.startswith('.') or dir_name in ('__pycache__', 'node_modules'):
                continue
                
            # Calculate the relative path for display
            rel_path = os.path.relpath(dir_path, ROOT_SEARCH_DIR)
            areas.append({
                "name": dir_name,
                "path": dir_path,
                "relative_path": rel_path,
                "depth": current_depth + 1
            })
    
    # Sort by name for better presentation
    areas.sort(key=lambda x: x["name"])
    return areas

def list_subareas(area_path: str, max_depth: int = MAX_DEPTH) -> List[Dict[str, str]]:
    """Lists all subareas (subdirectories) for a given area.
    
    Args:
        area_path (str): The path to the area directory.
        max_depth (int): Maximum depth to traverse. Default is set by MAX_DEPTH.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing subarea names and paths.
    """
    if not os.path.isdir(area_path):
        return []
        
    area_depth = area_path.count(os.sep)
    subareas = []
    
    for root, dirs, _ in os.walk(area_path):
        # Skip the area directory itself
        if root == area_path:
            continue
            
        # Calculate current depth relative to the area
        current_depth = root.count(os.sep) - area_depth
        if current_depth > max_depth:
            continue
            
        # Add the current directory as a subarea
        dir_name = os.path.basename(root)
        # Skip hidden directories and system folders
        if dir_name.startswith('.') or dir_name in ('__pycache__', 'node_modules'):
            continue
            
        rel_path = os.path.relpath(root, ROOT_SEARCH_DIR)
        subareas.append({
            "name": dir_name,
            "path": root,
            "relative_path": rel_path,
            "depth": current_depth
        })
    
    # Sort by name for better presentation
    subareas.sort(key=lambda x: x["name"])
    return subareas

def search_files_by_name(query: str, directory: Optional[str] = None, recursive: bool = True) -> List[Dict[str, str]]:
    """Search for files by name using fuzzy matching.
    
    Args:
        query (str): The search query string.
        directory (Optional[str]): The directory to search in. Defaults to ROOT_SEARCH_DIR.
        recursive (bool): Whether to search recursively. Defaults to True.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing file information.
    """
    if directory is None:
        directory = ROOT_SEARCH_DIR
    
    if not os.path.isdir(directory):
        return []
    
    results = []
    pattern = f"*{query}*"
    
    for root, _, files in os.walk(directory):
        if not recursive and root != directory:
            continue
            
        for filename in files:
            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                file_path = os.path.join(root, filename)
                try:
                    stats = os.stat(file_path)
                    created_time = datetime.datetime.fromtimestamp(stats.st_ctime)
                    modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                    
                    # Get file extension and determine if it's searchable
                    _, ext = os.path.splitext(filename)
                    is_searchable = ext.lower() in SEARCHABLE_EXTENSIONS
                    
                    results.append({
                        "name": filename,
                        "path": file_path,
                        "relative_path": os.path.relpath(file_path, ROOT_SEARCH_DIR),
                        "size": stats.st_size,
                        "created": created_time.isoformat(),
                        "modified": modified_time.isoformat(),
                        "is_searchable": is_searchable,
                        "mime_type": mimetypes.guess_type(filename)[0] or "unknown"
                    })
                except (FileNotFoundError, PermissionError):
                    continue
                    
                if len(results) >= MAX_RESULTS:
                    return results
    
    # Sort by name for consistency
    results.sort(key=lambda x: x["name"])
    return results

def search_files_by_date_created(start_date: str, end_date: Optional[str] = None, 
                                directory: Optional[str] = None) -> List[Dict[str, str]]:
    """Search for files by creation date.
    
    Args:
        start_date (str): The start date in ISO format (YYYY-MM-DD).
        end_date (Optional[str]): The end date in ISO format. If None, only files created on start_date are returned.
        directory (Optional[str]): The directory to search in. Defaults to ROOT_SEARCH_DIR.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing file information.
    """
    if directory is None:
        directory = ROOT_SEARCH_DIR
        
    if not os.path.isdir(directory):
        return []
    
    # Parse dates
    try:
        start_datetime = datetime.datetime.fromisoformat(start_date)
        if end_date:
            end_datetime = datetime.datetime.fromisoformat(end_date)
            # Set time to end of day
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
        else:
            # If no end date, set it to the end of the start date
            end_datetime = start_datetime.replace(hour=23, minute=59, second=59)
            start_datetime = start_datetime.replace(hour=0, minute=0, second=0)
    except ValueError:
        return []
    
    results = []
    
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                stats = os.stat(file_path)
                created_time = datetime.datetime.fromtimestamp(stats.st_ctime)
                
                if start_datetime <= created_time <= end_datetime:
                    modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                    
                    # Get file extension and determine if it's searchable
                    _, ext = os.path.splitext(filename)
                    is_searchable = ext.lower() in SEARCHABLE_EXTENSIONS
                    
                    results.append({
                        "name": filename,
                        "path": file_path,
                        "relative_path": os.path.relpath(file_path, ROOT_SEARCH_DIR),
                        "size": stats.st_size,
                        "created": created_time.isoformat(),
                        "modified": modified_time.isoformat(),
                        "is_searchable": is_searchable,
                        "mime_type": mimetypes.guess_type(filename)[0] or "unknown"
                    })
            except (FileNotFoundError, PermissionError):
                continue
                
            if len(results) >= MAX_RESULTS:
                return results
    
    # Sort by creation date, newest first
    results.sort(key=lambda x: x["created"], reverse=True)
    return results

def search_files_by_date_modified(start_date: str, end_date: Optional[str] = None, 
                                 directory: Optional[str] = None) -> List[Dict[str, str]]:
    """Search for files by modification date.
    
    Args:
        start_date (str): The start date in ISO format (YYYY-MM-DD).
        end_date (Optional[str]): The end date in ISO format. If None, only files modified on start_date are returned.
        directory (Optional[str]): The directory to search in. Defaults to ROOT_SEARCH_DIR.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing file information.
    """
    if directory is None:
        directory = ROOT_SEARCH_DIR
        
    if not os.path.isdir(directory):
        return []
    
    # Parse dates
    try:
        start_datetime = datetime.datetime.fromisoformat(start_date)
        if end_date:
            end_datetime = datetime.datetime.fromisoformat(end_date)
            # Set time to end of day
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
        else:
            # If no end date, set it to the end of the start date
            end_datetime = start_datetime.replace(hour=23, minute=59, second=59)
            start_datetime = start_datetime.replace(hour=0, minute=0, second=0)
    except ValueError:
        return []
    
    results = []
    
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                stats = os.stat(file_path)
                modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                
                if start_datetime <= modified_time <= end_datetime:
                    created_time = datetime.datetime.fromtimestamp(stats.st_ctime)
                    
                    # Get file extension and determine if it's searchable
                    _, ext = os.path.splitext(filename)
                    is_searchable = ext.lower() in SEARCHABLE_EXTENSIONS
                    
                    results.append({
                        "name": filename,
                        "path": file_path,
                        "relative_path": os.path.relpath(file_path, ROOT_SEARCH_DIR),
                        "size": stats.st_size,
                        "created": created_time.isoformat(),
                        "modified": modified_time.isoformat(),
                        "is_searchable": is_searchable,
                        "mime_type": mimetypes.guess_type(filename)[0] or "unknown"
                    })
            except (FileNotFoundError, PermissionError):
                continue
                
            if len(results) >= MAX_RESULTS:
                return results
    
    # Sort by modification date, newest first
    results.sort(key=lambda x: x["modified"], reverse=True)
    return results

def search_files_by_date_in_name(date_str: str, directory: Optional[str] = None) -> List[Dict[str, str]]:
    """Search for files that have a date in their name matching the provided date.
    
    Args:
        date_str (str): The date string to search for in ISO format (YYYY-MM-DD).
        directory (Optional[str]): The directory to search in. Defaults to ROOT_SEARCH_DIR.
        
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing file information.
    """
    if directory is None:
        directory = ROOT_SEARCH_DIR
        
    if not os.path.isdir(directory):
        return []
    
    # Validate date format
    try:
        date_obj = datetime.datetime.fromisoformat(date_str)
        # Different date formats to search for
        date_patterns = [
            date_obj.strftime("%Y-%m-%d"),  # ISO format: 2023-01-15
            date_obj.strftime("%Y_%m_%d"),  # Underscore format: 2023_01_15
            date_obj.strftime("%Y%m%d"),    # Compact format: 20230115
            date_obj.strftime("%d-%m-%Y"),  # European format: 15-01-2023
            date_obj.strftime("%m-%d-%Y"),  # US format: 01-15-2023
        ]
    except ValueError:
        return []
    
    results = []
    
    for root, _, files in os.walk(directory):
        for filename in files:
            # Check if any date pattern is in the filename
            if any(pattern in filename for pattern in date_patterns):
                file_path = os.path.join(root, filename)
                try:
                    stats = os.stat(file_path)
                    created_time = datetime.datetime.fromtimestamp(stats.st_ctime)
                    modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                    
                    # Get file extension and determine if it's searchable
                    _, ext = os.path.splitext(filename)
                    is_searchable = ext.lower() in SEARCHABLE_EXTENSIONS
                    
                    results.append({
                        "name": filename,
                        "path": file_path,
                        "relative_path": os.path.relpath(file_path, ROOT_SEARCH_DIR),
                        "size": stats.st_size,
                        "created": created_time.isoformat(),
                        "modified": modified_time.isoformat(),
                        "is_searchable": is_searchable,
                        "date_in_name": True,
                        "mime_type": mimetypes.guess_type(filename)[0] or "unknown"
                    })
                except (FileNotFoundError, PermissionError):
                    continue
                    
                if len(results) >= MAX_RESULTS:
                    return results
    
    # Sort by name for consistency
    results.sort(key=lambda x: x["name"])
    return results

def list_files(path: str, extensions: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Lists all files in a given directory with optional extension filtering.

    Args:
        path (str): The directory path to list files from.
        extensions (Optional[List[str]]): List of file extensions to filter by (e.g., ['.pdf', '.txt']).
    
    Returns:
        List[Dict[str, str]]: A list of dictionaries containing file information.
    """
    if not os.path.isdir(path):
        return []
        
    results = []
    
    try:
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            
            # Skip directories and check extensions if specified
            if os.path.isdir(file_path):
                continue
                
            _, ext = os.path.splitext(filename)
            if extensions and ext.lower() not in extensions:
                continue
                
            try:
                stats = os.stat(file_path)
                created_time = datetime.datetime.fromtimestamp(stats.st_ctime)
                modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                
                is_searchable = ext.lower() in SEARCHABLE_EXTENSIONS
                
                results.append({
                    "name": filename,
                    "path": file_path,
                    "relative_path": os.path.relpath(file_path, ROOT_SEARCH_DIR),
                    "size": stats.st_size,
                    "created": created_time.isoformat(),
                    "modified": modified_time.isoformat(),
                    "is_searchable": is_searchable,
                    "mime_type": mimetypes.guess_type(filename)[0] or "unknown"
                })
            except (FileNotFoundError, PermissionError):
                continue
                
    except (FileNotFoundError, PermissionError):
        return []
        
    # Sort by name for consistency
    results.sort(key=lambda x: x["name"])
    return results

def search_file_contents(query: str, directory: Optional[str] = None, 
                         max_files: int = 100) -> List[Dict[str, Union[str, List[str]]]]:
    """Search for text content within searchable files.
    
    Args:
        query (str): The text to search for.
        directory (Optional[str]): The directory to search in. Defaults to ROOT_SEARCH_DIR.
        max_files (int): Maximum number of files to search.
        
    Returns:
        List[Dict[str, Union[str, List[str]]]]: Files containing the query with matching line snippets.
    """
    if directory is None:
        directory = ROOT_SEARCH_DIR
        
    if not os.path.isdir(directory):
        return []
    
    results = []
    files_searched = 0
    
    for root, _, files in os.walk(directory):
        for filename in files:
            # Check if the file has a searchable extension
            _, ext = os.path.splitext(filename)
            if ext.lower() not in SEARCHABLE_EXTENSIONS:
                continue
                
            file_path = os.path.join(root, filename)
            try:
                # Read the file and search for the query
                file_size = os.path.getsize(file_path)
                
                # Skip files that are too large (>10MB) for content search
                if file_size > 10 * 1024 * 1024:
                    continue
                    
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                if query.lower() in content.lower():
                    # Find matching lines for context
                    lines = content.split('\n')
                    matches = []
                    
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            # Get context (lines before and after)
                            start = max(0, i - 1)
                            end = min(len(lines), i + 2)
                            context = [f"{lines[j]}" for j in range(start, end)]
                            matches.append({
                                "line_number": i + 1,
                                "context": context
                            })
                            
                            # Limit number of matches per file
                            if len(matches) >= 5:
                                break
                                
                    stats = os.stat(file_path)
                    created_time = datetime.datetime.fromtimestamp(stats.st_ctime)
                    modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                    
                    results.append({
                        "name": filename,
                        "path": file_path,
                        "relative_path": os.path.relpath(file_path, ROOT_SEARCH_DIR),
                        "size": stats.st_size,
                        "created": created_time.isoformat(),
                        "modified": modified_time.isoformat(),
                        "matches": matches,
                        "mime_type": mimetypes.guess_type(filename)[0] or "unknown"
                    })
                    
                    if len(results) >= MAX_RESULTS:
                        return results
                        
            except (UnicodeDecodeError, FileNotFoundError, PermissionError):
                continue
                
            files_searched += 1
            if files_searched >= max_files:
                break
                
        if files_searched >= max_files:
            break
    
    # Sort by number of matches, most relevant first
    results.sort(key=lambda x: len(x["matches"]), reverse=True)
    return results

def get_file_details(file_path: str) -> Dict[str, str]:
    """Get detailed information about a specific file.
    
    Args:
        file_path (str): The path to the file.
        
    Returns:
        Dict[str, str]: Detailed file information.
    """
    if not os.path.isfile(file_path):
        return {"error": "File not found"}
        
    try:
        stats = os.stat(file_path)
        created_time = datetime.datetime.fromtimestamp(stats.st_ctime)
        modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
        accessed_time = datetime.datetime.fromtimestamp(stats.st_atime)
        
        filename = os.path.basename(file_path)
        _, ext = os.path.splitext(filename)
        
        file_info = {
            "name": filename,
            "path": file_path,
            "relative_path": os.path.relpath(file_path, ROOT_SEARCH_DIR),
            "size": stats.st_size,
            "size_human": f"{stats.st_size / 1024:.1f} KB" if stats.st_size < 1024 * 1024 else f"{stats.st_size / (1024 * 1024):.2f} MB",
            "created": created_time.isoformat(),
            "modified": modified_time.isoformat(),
            "accessed": accessed_time.isoformat(),
            "extension": ext,
            "is_searchable": ext.lower() in SEARCHABLE_EXTENSIONS,
            "mime_type": mimetypes.guess_type(filename)[0] or "unknown"
        }
        
        # Try to extract date from filename if it follows YYYY-MM-DD pattern
        date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', filename)
        if date_match:
            file_info["date_in_name"] = date_match.group(1)
            
        return file_info
        
    except (FileNotFoundError, PermissionError) as e:
        return {"error": str(e)}

def read_file_content(file_path: str, max_size: int = 1024 * 1024) -> Dict[str, Union[str, int]]:
    """Read the content of a text file.
    
    Args:
        file_path (str): The path to the file.
        max_size (int): Maximum file size to read in bytes. Default is 1MB.
        
    Returns:
        Dict[str, Union[str, int]]: File content information.
    """
    if not os.path.isfile(file_path):
        return {"error": "File not found"}
        
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            return {
                "error": f"File too large to read ({file_size / (1024 * 1024):.2f} MB). Maximum size is {max_size / (1024 * 1024)} MB.",
                "file_size": file_size
            }
            
        # Check if file is binary
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in SEARCHABLE_EXTENSIONS:
            return {"error": "File appears to be binary or non-readable format"}
            
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        return {
            "content": content,
            "file_size": file_size,
            "encoding": "utf-8"
        }
        
    except (UnicodeDecodeError, FileNotFoundError, PermissionError) as e:
        return {"error": str(e)}

# Create the agent with all the tools
root_agent = Agent(
  name="file_finder",
  model="gemini-2.0-flash",
  #model="gemini-2.0-flash-live-001",
  description="An intelligent agent that helps find files and extract information from them using natural language.",
  instruction="""
You are an AI assistant that helps users find files and information in their file system.

You have access to the following tools:
1. list_areas: Lists all top-level directories (areas) in the search root.
2. list_subareas: Lists subdirectories for a given area.
3. search_files_by_name: Find files by name using fuzzy matching.
4. search_files_by_date_created: Find files created within a date range.
5. search_files_by_date_modified: Find files modified within a date range.
6. search_files_by_date_in_name: Find files with a specific date in the filename.
7. list_files: List all files in a specific directory.
8. search_file_contents: Search for text within files.
9. get_file_details: Get detailed metadata about a specific file.
10. read_file_content: Read the content of a text file.

When helping users:
- Ask clarifying questions if their request is too general.
- For searches, suggest narrowing down by category, date, or keywords.
- Present results in a clear, organized way.
- If there are many results, summarize and suggest ways to narrow down.
- When showing file information, include relevant details like dates and paths.
- For file content searches, highlight the matching text.

Always respect the user's file organization system. If they talk about specific areas like "medical", "pets", "travel", etc., use those categories in your search.
  """,
  tools=[
    list_areas,
    list_subareas,
    search_files_by_name,
    search_files_by_date_created,
    search_files_by_date_modified,
    search_files_by_date_in_name,
    list_files,
    search_file_contents,
    get_file_details,
    read_file_content
  ],
)
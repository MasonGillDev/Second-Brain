"""
Code ingestion.

Parses source code files and extracts comments, docstrings, and function
signatures. Stores them in the ChromaDB code_context collection with
metadata for file path, line number, and context type.

Usage:
    python -m memory.ingest_code /path/to/codebase
"""

import os
import re
import ast
import hashlib
import argparse
import config
from memory.vector_store import VectorStore


# Language support: extension -> parser function
SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".swift": "swift",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "target", "vendor",
    ".tox", "eggs", "*.egg-info", ".mypy_cache", ".pytest_cache",
}


def file_hash(filepath: str) -> str:
    """MD5 hash for change detection."""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _should_skip_dir(dirname: str) -> bool:
    """Check if directory should be skipped."""
    return dirname in SKIP_DIRS or dirname.startswith(".")


# =============================================================================
# PYTHON PARSER (AST-based, most accurate)
# =============================================================================

def _parse_python(filepath: str, source: str) -> list[dict]:
    """Extract comments and docstrings from Python using AST."""
    chunks = []

    # Extract module-level docstring
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Fall back to regex if AST fails
        return _parse_generic(filepath, source, "#")

    module_doc = ast.get_docstring(tree)
    if module_doc:
        chunks.append({
            "text": module_doc,
            "metadata": {
                "file_path": filepath,
                "line_number": 1,
                "type": "module_doc",
                "function_name": "",
                "class_name": "",
                "language": "python",
            }
        })

    # Walk AST for classes and top-level functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node)

            # Always store class signature
            base_names = []
            for base in node.bases:
                try:
                    base_names.append(ast.unparse(base))
                except Exception:
                    pass
            bases_str = f"({', '.join(base_names)})" if base_names else ""
            sig_text = f"class {node.name}{bases_str}"
            if class_doc:
                sig_text += f": {class_doc}"

            chunks.append({
                "text": sig_text,
                "metadata": {
                    "file_path": filepath,
                    "line_number": node.lineno,
                    "type": "class_doc" if class_doc else "class_sig",
                    "function_name": "",
                    "class_name": node.name,
                    "language": "python",
                }
            })

            # Methods within the class
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_doc = ast.get_docstring(item)
                    sig = _python_signature(item)
                    sig_text = f"{node.name}.{sig}"
                    if method_doc:
                        sig_text += f": {method_doc}"

                    chunks.append({
                        "text": sig_text,
                        "metadata": {
                            "file_path": filepath,
                            "line_number": item.lineno,
                            "type": "method_doc" if method_doc else "method_sig",
                            "function_name": item.name,
                            "class_name": node.name,
                            "language": "python",
                        }
                    })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_doc = ast.get_docstring(node)
            sig = _python_signature(node)
            sig_text = sig
            if func_doc:
                sig_text += f": {func_doc}"

            chunks.append({
                "text": sig_text,
                "metadata": {
                    "file_path": filepath,
                    "line_number": node.lineno,
                    "type": "function_doc" if func_doc else "function_sig",
                    "function_name": node.name,
                    "class_name": "",
                    "language": "python",
                }
            })

    # Extract standalone comments (lines starting with #)
    comment_blocks = _extract_comment_blocks(source, "#")
    for block in comment_blocks:
        # Skip trivial comments
        if len(block["text"]) < config.CODE_INGEST_MIN_COMMENT_LENGTH:
            continue
        block["metadata"].update({
            "file_path": filepath,
            "language": "python",
        })
        chunks.append(block)

    return chunks


def _python_signature(node: ast.FunctionDef) -> str:
    """Build a readable function signature from AST."""
    args = []
    for arg in node.args.args:
        name = arg.arg
        if arg.annotation:
            try:
                name += f": {ast.unparse(arg.annotation)}"
            except Exception:
                pass
        args.append(name)

    # Remove 'self' and 'cls' for readability
    if args and args[0] in ("self", "cls"):
        args = args[1:]

    ret = ""
    if node.returns:
        try:
            ret = f" -> {ast.unparse(node.returns)}"
        except Exception:
            pass

    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return f"{prefix}{node.name}({', '.join(args)}){ret}"


# =============================================================================
# GENERIC PARSER (regex-based, works for most languages)
# =============================================================================

def _parse_generic(filepath: str, source: str, single_comment: str = "//") -> list[dict]:
    """Extract comments from any language using regex patterns."""
    chunks = []
    language = SUPPORTED_EXTENSIONS.get(os.path.splitext(filepath)[1], "unknown")

    # Extract block comments (/* ... */ or /** ... */)
    block_pattern = r'/\*\*?(.*?)\*/'
    for match in re.finditer(block_pattern, source, re.DOTALL):
        text = match.group(1).strip()
        # Clean leading * from each line (JSDoc/Javadoc style)
        text = re.sub(r'^\s*\*\s?', '', text, flags=re.MULTILINE).strip()

        if len(text) < config.CODE_INGEST_MIN_COMMENT_LENGTH:
            continue

        line_number = source[:match.start()].count('\n') + 1

        # Try to find what this comment is attached to (next non-empty line after comment)
        after = source[match.end():].lstrip('\n')
        context_name = _extract_declaration_name(after, language)

        chunks.append({
            "text": f"{context_name}: {text}" if context_name else text,
            "metadata": {
                "file_path": filepath,
                "line_number": line_number,
                "type": "block_comment",
                "function_name": context_name or "",
                "class_name": "",
                "language": language,
            }
        })

    # Extract single-line comment blocks
    comment_blocks = _extract_comment_blocks(source, single_comment)
    for block in comment_blocks:
        if len(block["text"]) < config.CODE_INGEST_MIN_COMMENT_LENGTH:
            continue
        block["metadata"].update({
            "file_path": filepath,
            "language": language,
        })
        chunks.append(block)

    # Extract bare declarations (functions/classes without comments)
    commented_lines = set()
    for c in chunks:
        commented_lines.add(c["metadata"].get("line_number", 0))

    lines = source.split('\n')
    for i, line in enumerate(lines):
        line_num = i + 1
        if line_num in commented_lines:
            continue
        name = _extract_declaration_name(line, language)
        if name:
            # Get the full signature line, cleaned up
            sig = line.strip()
            # Skip private/underscore helpers in non-Python (Python handled by AST)
            if sig.startswith("_"):
                continue
            chunks.append({
                "text": sig,
                "metadata": {
                    "file_path": filepath,
                    "line_number": line_num,
                    "type": "signature",
                    "function_name": name,
                    "class_name": "",
                    "language": language,
                }
            })

    return chunks


def _extract_comment_blocks(source: str, prefix: str) -> list[dict]:
    """Group consecutive single-line comments into blocks."""
    lines = source.split('\n')
    blocks = []
    current_block = []
    block_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(prefix) and not stripped.startswith(prefix + "!"):
            comment_text = stripped[len(prefix):].strip()
            # Skip trivial comments
            if comment_text.lower() in ("", "todo", "fixme", "hack", "noqa"):
                continue
            if not current_block:
                block_start = i + 1  # 1-indexed
            current_block.append(comment_text)
        else:
            if current_block and len(current_block) >= config.CODE_INGEST_MIN_COMMENT_LINES:
                combined = " ".join(current_block)

                # Check what follows the comment block
                context_name = ""
                if stripped:
                    lang = "unknown"
                    context_name = _extract_declaration_name(stripped, lang)

                blocks.append({
                    "text": f"{context_name}: {combined}" if context_name else combined,
                    "metadata": {
                        "line_number": block_start,
                        "type": "comment_block",
                        "function_name": context_name or "",
                        "class_name": "",
                    }
                })
            current_block = []

    # Handle trailing block
    if current_block and len(current_block) >= config.CODE_INGEST_MIN_COMMENT_LINES:
        combined = " ".join(current_block)
        blocks.append({
            "text": combined,
            "metadata": {
                "line_number": block_start,
                "type": "comment_block",
                "function_name": "",
                "class_name": "",
            }
        })

    return blocks


def _extract_declaration_name(line: str, language: str) -> str:
    """Try to extract a function/class name from a declaration line."""
    patterns = [
        # Python
        r'^(?:async\s+)?def\s+(\w+)',
        r'^class\s+(\w+)',
        # JS/TS
        r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)',
        r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=',
        r'^(?:export\s+)?class\s+(\w+)',
        # Go
        r'^func\s+(?:\([^)]+\)\s+)?(\w+)',
        r'^type\s+(\w+)',
        # Rust
        r'^(?:pub\s+)?fn\s+(\w+)',
        r'^(?:pub\s+)?struct\s+(\w+)',
        r'^(?:pub\s+)?enum\s+(\w+)',
        # Java/Swift
        r'^(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|enum)\s+(\w+)',
        r'^(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(',
    ]
    for pattern in patterns:
        match = re.match(pattern, line.strip())
        if match:
            return match.group(1)
    return ""


# =============================================================================
# DISPATCH
# =============================================================================

def _get_parser(filepath: str):
    """Return the appropriate parser for a file."""
    ext = os.path.splitext(filepath)[1].lower()
    language = SUPPORTED_EXTENSIONS.get(ext)
    if not language:
        return None

    if language == "python":
        return _parse_python

    # All others use generic parser with appropriate comment prefix
    comment_prefix = "//"
    if language == "ruby":
        comment_prefix = "#"
    return lambda fp, src: _parse_generic(fp, src, comment_prefix)


# =============================================================================
# MAIN INGESTION
# =============================================================================

def ingest_codebase(path: str, vector_store: VectorStore | None = None) -> int:
    """
    Ingest a file or directory into the code_context collection.

    Args:
        path: File or directory path to ingest
        vector_store: VectorStore instance (creates one if not provided)

    Returns:
        Number of chunks stored
    """
    if vector_store is None:
        vector_store = VectorStore()

    if os.path.isfile(path):
        return _ingest_file(path, vector_store)

    total = 0
    for root, dirs, files in os.walk(path):
        # Filter out skip dirs in-place
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]

        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)

            # Skip files over size limit
            if os.path.getsize(filepath) > config.CODE_INGEST_MAX_FILE_SIZE:
                if config.LOG_TOKEN_USAGE:
                    print(f"  [code_ingest] SKIP (too large): {filepath}")
                continue

            added = _ingest_file(filepath, vector_store)
            total += added

    if config.LOG_TOKEN_USAGE:
        print(f"  [code_ingest] Total: {total} chunks from {path}")

    return total


def _ingest_file(filepath: str, vector_store: VectorStore) -> int:
    """Ingest a single file. Returns number of chunks added."""
    current_hash = file_hash(filepath)

    # Check if already ingested with same hash
    existing = vector_store.collections["code_context"].get(
        where={"$and": [{"file_path": filepath}, {"file_hash": current_hash}]}
    )
    if existing["ids"]:
        return 0  # Already ingested this version

    # Remove old version
    vector_store.delete_by_metadata("code_context", {"file_path": filepath})

    # Read and parse
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return 0

    parser = _get_parser(filepath)
    if not parser:
        return 0

    chunks = parser(filepath, source)
    if not chunks:
        return 0

    # Store chunks
    texts = [c["text"] for c in chunks]
    metadatas = [
        {**c["metadata"], "file_hash": current_hash}
        for c in chunks
    ]
    ids = [
        f"code_{os.path.basename(filepath)}_{i}_{int(hashlib.md5(t.encode()).hexdigest()[:8], 16)}"
        for i, t in enumerate(texts)
    ]

    vector_store.add_batch("code_context", texts, metadatas, ids)

    if config.LOG_TOKEN_USAGE:
        print(f"  [code_ingest] {filepath}: {len(chunks)} chunks")

    return len(chunks)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest code comments and docstrings into Second Brain memory."
    )
    parser.add_argument("path", help="File or directory to ingest")
    parser.add_argument("--stats", action="store_true", help="Show stats after ingestion")
    args = parser.parse_args()

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        print(f"Error: {path} does not exist")
        exit(1)

    print(f"Ingesting code from: {path}")
    vs = VectorStore()
    count = ingest_codebase(path, vs)
    print(f"Done. {count} chunks ingested into code_context collection.")

    if args.stats:
        stats = vs.get_stats()
        print(f"\nCollection stats:")
        for name, n in stats.items():
            print(f"  {name}: {n}")

#!/usr/bin/env python3
"""
Simple repository analysis for InGest-LLM.as without external dependencies
"""

import ast
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def analyze_python_file(file_path):
    """Analyze a Python file using AST."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        tree = ast.parse(content)

        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args),
                        "decorators": len(node.decorator_list),
                    }
                )
            elif isinstance(node, ast.ClassDef):
                classes.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len(
                            [n for n in node.body if isinstance(n, ast.FunctionDef)]
                        ),
                        "bases": len(node.bases),
                    }
                )
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                else:
                    imports.append(node.module if node.module else "")

        lines = content.split("\n")
        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "lines": len(lines),
            "size": len(content),
            "complexity_score": len(functions) + len(classes) * 2,  # Simple complexity
        }
    except Exception as e:
        return {"error": str(e), "lines": 0, "size": 0, "complexity_score": 0}


def analyze_repository():
    """Analyze the current repository."""

    print("=" * 70)
    print("INGEST-LLM.AS REPOSITORY ANALYSIS REPORT")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Repository: {Path.cwd()}")
    print()

    # File patterns to analyze
    include_patterns = [
        "**/*.py",
        "**/*.md",
        "**/*.yml",
        "**/*.yaml",
        "**/*.toml",
        "**/*.json",
    ]
    exclude_patterns = [
        "__pycache__",
        ".pytest_cache",
        ".git",
        ".venv",
        "venv",
        ".mypy_cache",
        "*.egg-info",
        "dist",
        "build",
    ]

    # Discover files
    all_files = []
    for pattern in include_patterns:
        for file_path in Path(".").glob(pattern):
            if file_path.is_file():
                # Check if should exclude
                should_exclude = False
                for exclude in exclude_patterns:
                    if exclude in str(file_path):
                        should_exclude = True
                        break

                if not should_exclude:
                    all_files.append(file_path)

    # Analyze files
    file_analysis = defaultdict(list)
    total_size = 0
    total_lines = 0
    total_functions = 0
    total_classes = 0
    total_complexity = 0

    python_files = []

    print("ANALYZING FILES...")
    print("-" * 30)

    for file_path in all_files:
        size = file_path.stat().st_size
        total_size += size
        extension = file_path.suffix or "no_extension"

        file_info = {"path": str(file_path), "size": size, "extension": extension}

        if extension == ".py":
            analysis = analyze_python_file(file_path)
            file_info.update(analysis)

            if "error" not in analysis:
                total_lines += analysis["lines"]
                total_functions += len(analysis["functions"])
                total_classes += len(analysis["classes"])
                total_complexity += analysis["complexity_score"]
                python_files.append(file_info)
        else:
            # Count lines for non-Python files
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = len(f.readlines())
                file_info["lines"] = lines
                total_lines += lines
            except:
                file_info["lines"] = 0

        file_analysis[extension].append(file_info)

    # Generate report
    print(f"Files discovered: {len(all_files)}")
    print()

    print("OVERALL METRICS")
    print("-" * 30)
    print(f"Total Files: {len(all_files)}")
    print(f"Total Size: {total_size / 1024:.1f} KB")
    print(f"Total Lines: {total_lines:,}")
    print(f"Python Files: {len(python_files)}")
    print(f"Total Functions: {total_functions}")
    print(f"Total Classes: {total_classes}")
    if python_files:
        print(f"Average Complexity: {total_complexity / len(python_files):.2f}")
    print()

    print("FILE TYPE DISTRIBUTION")
    print("-" * 30)
    for ext, files in sorted(file_analysis.items()):
        total_ext_size = sum(f["size"] for f in files)
        print(f"{ext:>12}: {len(files):>3} files ({total_ext_size / 1024:>6.1f} KB)")
    print()

    # Largest files
    all_files_sorted = []
    for files in file_analysis.values():
        all_files_sorted.extend(files)

    largest_files = sorted(all_files_sorted, key=lambda x: x["size"], reverse=True)[:10]

    print("LARGEST FILES")
    print("-" * 30)
    for i, file_info in enumerate(largest_files, 1):
        size_kb = file_info["size"] / 1024
        print(f"{i:>2}. {file_info['path']:<45} ({size_kb:>6.1f} KB)")
    print()

    # Most complex Python files
    if python_files:
        complex_files = sorted(
            python_files, key=lambda x: x.get("complexity_score", 0), reverse=True
        )[:10]

        print("MOST COMPLEX PYTHON FILES")
        print("-" * 30)
        for i, file_info in enumerate(complex_files, 1):
            complexity = file_info.get("complexity_score", 0)
            funcs = len(file_info.get("functions", []))
            classes = len(file_info.get("classes", []))
            print(
                f"{i:>2}. {file_info['path']:<35} (complexity: {complexity:>3}, funcs: {funcs}, classes: {classes})"
            )
        print()

    # Python module analysis
    if python_files:
        print("PYTHON CODE ANALYSIS")
        print("-" * 30)

        # Function analysis
        all_functions = []
        for file_info in python_files:
            for func in file_info.get("functions", []):
                func["file"] = file_info["path"]
                all_functions.append(func)

        # Class analysis
        all_classes = []
        for file_info in python_files:
            for cls in file_info.get("classes", []):
                cls["file"] = file_info["path"]
                all_classes.append(cls)

        print(f"Functions per file: {total_functions / len(python_files):.1f}")
        print(f"Classes per file: {total_classes / len(python_files):.1f}")
        print(f"Lines per file: {total_lines / len(all_files):.1f}")

        if all_functions:
            avg_args = sum(f.get("args", 0) for f in all_functions) / len(all_functions)
            print(f"Average function arguments: {avg_args:.1f}")
        print()

    # Test coverage analysis
    test_files = [f for f in all_files if "test" in str(f).lower()]
    py_test_files = [f for f in python_files if "test" in f["path"].lower()]

    print("TEST COVERAGE ANALYSIS")
    print("-" * 30)
    print(f"Test Files: {len(test_files)}")
    print(f"Python Test Files: {len(py_test_files)}")
    if python_files:
        test_ratio = len(py_test_files) / len(python_files) * 100
        print(f"Test Coverage Ratio: {test_ratio:.1f}%")
    print()

    # Project structure analysis
    print("PROJECT STRUCTURE")
    print("-" * 30)

    directories = set()
    for file_path in all_files:
        parts = Path(file_path).parts
        for i in range(1, len(parts)):
            directories.add("/".join(parts[:i]))

    print(
        f"Directory depth: {max(len(Path(f).parts) for f in all_files) if all_files else 0}"
    )
    print(f"Unique directories: {len(directories)}")

    # Main directories
    main_dirs = defaultdict(int)
    for file_path in all_files:
        if len(Path(file_path).parts) > 1:
            main_dirs[Path(file_path).parts[0]] += 1

    print("Main directories:")
    for dir_name, count in sorted(main_dirs.items()):
        print(f"  {dir_name}: {count} files")
    print()

    # Recommendations
    print("RECOMMENDATIONS")
    print("-" * 30)

    if python_files:
        avg_complexity = total_complexity / len(python_files)
        if avg_complexity > 10:
            print("• High average complexity detected - consider refactoring")

        if total_functions / len(python_files) > 15:
            print("• Many functions per file - consider splitting into modules")

        if len(py_test_files) / len(python_files) < 0.3:
            print("• Low test coverage - consider adding more tests")

    if any(f["size"] > 100000 for f in largest_files):
        print("• Large files detected - consider splitting for maintainability")

    if len(python_files) > 30:
        print("• Consider organizing code into packages")

    print("• Repository structure appears well-organized")
    print()

    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("This analysis provides insights into the InGest-LLM.as codebase structure,")
    print(
        "complexity, and organization. Use these metrics to guide development decisions."
    )
    print("=" * 70)


if __name__ == "__main__":
    analyze_repository()

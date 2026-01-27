"""
Unit tests for smart_parser.py code block extraction.

Phase 7: TN-CODE-01 - Code Block Extraction Tests
"""

import pytest

from omega_kg.smart_parser import SmartParser, CodeBlock, CODE_BLOCK_REGEX


class TestCodeBlockRegex:
    """Tests for the code block regex pattern."""

    def test_python_code_block(self) -> None:
        """Test detection of Python code blocks."""
        content = """
Some text here.

```python
def hello():
    print("world")
```

More text.
"""
        matches = CODE_BLOCK_REGEX.findall(content)
        assert len(matches) == 1
        assert matches[0][0] == "python"
        assert "def hello():" in matches[0][1]

    def test_javascript_code_block(self) -> None:
        """Test detection of JavaScript code blocks."""
        content = """
```javascript
const x = 42;
console.log(x);
```
"""
        matches = CODE_BLOCK_REGEX.findall(content)
        assert len(matches) == 1
        assert matches[0][0] == "javascript"
        assert "const x = 42;" in matches[0][1]

    def test_code_block_without_language(self) -> None:
        """Test code blocks without specified language."""
        content = """
```
some plain text code
more lines
```
"""
        matches = CODE_BLOCK_REGEX.findall(content)
        assert len(matches) == 1
        assert matches[0][0] == ""
        assert "some plain text code" in matches[0][1]

    def test_multiple_code_blocks(self) -> None:
        """Test detection of multiple code blocks."""
        content = """
```python
def foo():
    pass
```

Some text.

```javascript
const bar = 1;
```

```rust
fn baz() {}
```
"""
        matches = CODE_BLOCK_REGEX.findall(content)
        assert len(matches) == 3
        assert matches[0][0] == "python"
        assert matches[1][0] == "javascript"
        assert matches[2][0] == "rust"

    def test_nested_code_blocks_not_detected(self) -> None:
        """Test that nested code blocks are not incorrectly detected."""
        content = """
```python
def outer():
    ```
    inner_code()
    ```
```
"""
        matches = CODE_BLOCK_REGEX.findall(content)
        # Should match outer block only
        assert len(matches) == 1


class TestCodeBlockDataClass:
    """Tests for the CodeBlock dataclass."""

    def test_codeblock_creation(self) -> None:
        """Test CodeBlock instantiation with auto hash generation."""
        block = CodeBlock(
            language="python",
            content="print('hello')",
            block_index=0,
        )
        assert block.language == "python"
        assert block.content == "print('hello')"
        assert block.block_index == 0
        assert block.content_hash is not None
        assert len(block.content_hash) == 16

    def test_same_content_same_hash(self) -> None:
        """Test that identical content produces identical hashes."""
        block1 = CodeBlock(language="python", content="x = 1", block_index=0)
        block2 = CodeBlock(language="python", content="x = 1", block_index=0)
        assert block1.content_hash == block2.content_hash

    def test_different_content_different_hash(self) -> None:
        """Test that different content produces different hashes."""
        block1 = CodeBlock(language="python", content="x = 1", block_index=0)
        block2 = CodeBlock(language="python", content="x = 2", block_index=0)
        assert block1.content_hash != block2.content_hash

    def test_different_language_different_hash(self) -> None:
        """Test that different languages produce different hashes."""
        block1 = CodeBlock(language="python", content="x = 1", block_index=0)
        block2 = CodeBlock(language="javascript", content="x = 1", block_index=0)
        assert block1.content_hash != block2.content_hash


class TestSmartParserCodeBlockExtraction:
    """Tests for SmartParser._extract_code_blocks method."""

    @pytest.fixture
    def parser(self) -> SmartParser:
        """Create a SmartParser instance for testing."""
        return SmartParser()

    def test_no_code_blocks(self, parser: SmartParser) -> None:
        """Test extraction returns empty list when no code blocks present."""
        content = "Just plain text without any code blocks."
        blocks = parser._extract_code_blocks(content)
        assert blocks == []

    def test_single_code_block(self, parser: SmartParser) -> None:
        """Test extraction of a single code block."""
        content = """
# Title

Some text.

```python
def add(a, b):
    return a + b
```

More text.
"""
        blocks = parser._extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert "def add" in blocks[0].content
        assert blocks[0].block_index == 0

    def test_multiple_code_blocks(self, parser: SmartParser) -> None:
        """Test extraction of multiple code blocks with correct indexing."""
        content = """
```python
def foo():
    pass
```

```javascript
const bar = 42;
```

```rust
fn baz() {}
```
"""
        blocks = parser._extract_code_blocks(content)
        assert len(blocks) == 3

        assert blocks[0].language == "python"
        assert blocks[0].block_index == 0

        assert blocks[1].language == "javascript"
        assert blocks[1].block_index == 1

        assert blocks[2].language == "rust"
        assert blocks[2].block_index == 2

    def test_code_block_with_empty_language(self, parser: SmartParser) -> None:
        """Test that empty language defaults to 'text'."""
        content = "```\nsome code\n```"
        blocks = parser._extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "text"

    def test_code_block_content_stripping(self, parser: SmartParser) -> None:
        """Test that trailing newlines are stripped from content."""
        content = "```python\nprint('hello')\n```"
        blocks = parser._extract_code_blocks(content)
        assert len(blocks) == 1
        # Content should not have trailing newline before closing ```
        assert blocks[0].content.endswith("print('hello')")

    def test_multiline_code_block_content(self, parser: SmartParser) -> None:
        """Test multiline code block content is preserved."""
        content = """```python
def complex_function():
    if True:
        for i in range(10):
            print(i)
    return 0
```"""
        blocks = parser._extract_code_blocks(content)
        assert len(blocks) == 1
        assert "for i in range(10)" in blocks[0].content
        assert "return 0" in blocks[0].content

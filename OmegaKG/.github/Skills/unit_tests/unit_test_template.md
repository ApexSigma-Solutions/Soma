---
created: Sat, 27th December 2025 11:28
modified: Sat, 27th December 2025 11:30
---

```python
# test_template.txt (Example for Python/Pytest)
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_dependency():
    """Mock external dependencies here."""
    return Mock()

def test_feature_name_scenario_expected_behavior(mock_dependency):
    """
    Test Case: [Feature Name]
    Scenario: [Specific Scenario, e.g., Invalid Input]
    Expected: [Expected Outcome, e.g., Raise ValueError]
    """
    # Arrange
    data = ...

    # Act
    result = feature_function(data)

    # Assert
    assert result == ...
```

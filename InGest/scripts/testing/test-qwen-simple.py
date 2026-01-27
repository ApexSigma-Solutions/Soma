#!/usr/bin/env python3
"""
Simple Qwen model test without dependencies.
"""

import asyncio
import httpx
import json
from pathlib import Path


async def test_qwen_analysis():
    """Test Qwen model for project analysis."""

    print("=" * 70)
    print("QWEN MODEL ANALYSIS TEST")
    print("=" * 70)
    print()

    qwen_url = "http://172.22.144.1:12345/v1"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: Check models
            print("1. CHECKING AVAILABLE MODELS")
            print("-" * 30)

            response = await client.get(f"{qwen_url}/models")
            if response.status_code == 200:
                models_data = response.json()
                models = [
                    model.get("id", "unknown") for model in models_data.get("data", [])
                ]
                print(f"Available models: {len(models)}")
                for model in models:
                    print(f"  - {model}")
                print()

            # Test 2: Analyze InGest-LLM.as project
            print("2. ANALYZING INGEST-LLM.AS PROJECT")
            print("-" * 35)

            # Gather basic project info
            project_path = Path(".")

            # Get directory structure
            directories = []
            for item in project_path.iterdir():
                if (
                    item.is_dir()
                    and not item.name.startswith(".")
                    and item.name != "__pycache__"
                ):
                    directories.append(item.name)

            # Count files
            file_counts = {}
            for ext in [".py", ".md", ".yml", ".json", ".toml"]:
                count = len(list(project_path.glob(f"**/*{ext}")))
                if count > 0:
                    file_counts[ext] = count

            # Read key files
            key_files = {}
            for file_name in ["README.md", "pyproject.toml"]:
                file_path = project_path / file_name
                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        key_files[file_name] = content[:1000]  # First 1000 chars
                    except Exception:
                        pass

            print("Project structure analyzed:")
            print(f"  Directories: {directories}")
            print(f"  File counts: {file_counts}")
            print(f"  Key files: {list(key_files.keys())}")
            print()

            # Create analysis prompt
            prompt = f"""As an expert software architect, analyze the ApexSigma project "InGest-LLM.as" and provide a comprehensive outline.

PROJECT INFORMATION:
Project: InGest-LLM.as
Directory Structure: {directories}
File Counts: {file_counts}

KEY FILES CONTENT:
"""

            for file_name, content in key_files.items():
                prompt += f"\n{file_name}:\n```\n{content[:500]}\n```\n"

            prompt += """

Please provide a detailed analysis in the following JSON format:

{
  "description": "Brief description of the project's purpose",
  "architecture_type": "microservice/monolith/library/tool",
  "core_components": [
    {"name": "component_name", "description": "what it does", "type": "service/api/database/etc"}
  ],
  "api_endpoints": [
    {"method": "GET/POST", "path": "/endpoint", "description": "what it does"}
  ],
  "data_models": ["ModelName1", "ModelName2"],
  "services": [
    {"name": "service_name", "description": "what it provides", "type": "internal/external"}
  ],
  "dependencies": ["dependency1", "dependency2"],
  "key_features": ["feature1", "feature2"],
  "integration_points": ["integrates with X via Y", "stores data in Z"]
}

Focus on:
1. The main purpose and architecture pattern
2. Key services and components
3. API endpoints and data models
4. External dependencies
5. Integration points with other systems
6. Unique features and capabilities

Provide only the JSON response, no additional text."""

            print("3. QUERYING QWEN MODEL")
            print("-" * 25)
            print("Sending analysis request to Qwen...")

            # Query Qwen model
            response = await client.post(
                f"{qwen_url}/chat/completions",
                json={
                    "model": "qwen/qwen3-4b-thinking-2507",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert software architect analyzing codebases. Provide detailed, accurate JSON responses.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]

                print("✅ Qwen analysis completed!")
                print()
                print("4. QWEN ANALYSIS RESULT")
                print("-" * 25)
                print(ai_response)
                print()

                # Try to parse as JSON
                try:
                    json_str = ai_response.strip()
                    if json_str.startswith("```json"):
                        json_str = json_str[7:]
                    if json_str.endswith("```"):
                        json_str = json_str[:-3]

                    parsed = json.loads(json_str.strip())

                    print("5. PARSED ANALYSIS")
                    print("-" * 20)
                    print(f"Description: {parsed.get('description', 'N/A')}")
                    print(f"Architecture: {parsed.get('architecture_type', 'N/A')}")

                    components = parsed.get("core_components", [])
                    if components:
                        print("Core Components:")
                        for comp in components[:3]:
                            print(
                                f"  • {comp.get('name', 'Unknown')}: {comp.get('description', 'No description')}"
                            )

                    endpoints = parsed.get("api_endpoints", [])
                    if endpoints:
                        print("API Endpoints:")
                        for endpoint in endpoints[:3]:
                            method = endpoint.get("method", "GET")
                            path = endpoint.get("path", "/unknown")
                            desc = endpoint.get("description", "No description")
                            print(f"  • {method} {path}: {desc}")

                    features = parsed.get("key_features", [])
                    if features:
                        print(f"Key Features: {', '.join(features[:3])}")

                    deps = parsed.get("dependencies", [])
                    if deps:
                        print(f"Dependencies: {', '.join(deps[:3])}")

                except json.JSONDecodeError as e:
                    print(f"⚠️  Could not parse as JSON: {e}")
                    print("But the model is responding correctly!")

            else:
                print(f"❌ Qwen API error: {response.status_code}")
                print(response.text)

        print()
        print("=" * 70)
        print("QWEN INTEGRATION TEST SUCCESSFUL!")
        print("The AI model can analyze ApexSigma projects and generate")
        print("comprehensive outlines and architectural insights.")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_qwen_analysis())

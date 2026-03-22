#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback

def test_imports():
    """Test all imports from the migrated structure"""
    tests = [
        ("app.api.routes", "router"),
        ("app.service", "TaskService"),
        ("app.agent.agent", "WorkflowAgent"),
        ("app.domain.models", "TaskContext"),
        ("app.core.llm_client", "LLMClient"),
        ("app.tools.word.reader", "DocxReader"),
        ("app.tools.word.writer", "DocxWriter"),
        ("app.utils.json_utils", "extract_json_object"),
        ("app.agent.planner", "WorkflowPlanner"),
        ("app.agent.executor", "StepExecutor"),
    ]
    
    success_count = 0
    failed_tests = []
    
    for module, symbol in tests:
        try:
            mod = __import__(module, fromlist=[symbol])
            getattr(mod, symbol)
            print(f"✓ {module}.{symbol}")
            success_count += 1
        except Exception as e:
            print(f"✗ {module}.{symbol}: {e}")
            failed_tests.append((module, symbol, str(e)))
    
    print(f"\n{'='*60}")
    print(f"Results: {success_count}/{len(tests)} tests passed")
    
    if failed_tests:
        print("\nFailed tests:")
        for module, symbol, error in failed_tests:
            print(f"  - {module}.{symbol}")
            print(f"    Error: {error}")
        return False
    
    print("\nAll imports successful! ✓")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

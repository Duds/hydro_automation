#!/usr/bin/env python3
"""Simple test runner to verify tests can import and basic structure works."""

import sys
import importlib.util
from pathlib import Path

def test_import(module_name):
    """Test if a module can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False, f"Module '{module_name}' not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    """Run import tests for key modules."""
    print("=" * 60)
    print("Testing Module Imports")
    print("=" * 60)
    
    modules_to_test = [
        "src.core.scheduler_interface",
        "src.core.config_schema",
        "src.core.config_validator",
        "src.core.scheduler_factory",
        "src.services.device_service",
        "src.services.environmental_service",
        "src.services.service_factory",
        "src.schedulers.interval_scheduler",
        "src.schedulers.time_based_scheduler",
        "src.device.tapo_controller",
        "src.data.daylight",
        "src.data.bom_temperature",
        "src.main",
    ]
    
    failed = []
    passed = []
    
    for module_name in modules_to_test:
        success, error = test_import(module_name)
        if success:
            print(f"✅ {module_name}")
            passed.append(module_name)
        else:
            print(f"❌ {module_name}: {error}")
            failed.append((module_name, error))
    
    print("\n" + "=" * 60)
    print(f"Results: {len(passed)} passed, {len(failed)} failed")
    print("=" * 60)
    
    if failed:
        print("\nFailed imports:")
        for module_name, error in failed:
            print(f"  - {module_name}: {error}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


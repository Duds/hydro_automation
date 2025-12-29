# Cleanup Log

This document tracks files that have been cleaned up after the refactor.

## Files Removed

### Old Scheduler Files
- ❌ `src/scheduler.py` - Already removed (replaced by `src/schedulers/interval_scheduler.py`)
- ❌ `src/time_scheduler.py` - Already removed (replaced by `src/schedulers/time_based_scheduler.py`)

### Test Scripts in src/ (Outdated Config Format)
- ❌ `src/test_on_off.py` - Uses old config format, should be moved to tests/ or updated
- ❌ `src/test_plugp100.py` - Test script, should be in tests/ directory
- ❌ `src/test_plugp100_factory.py` - Test script, should be in tests/ directory
- ❌ `src/test_plugp100_v2.py` - Test script, should be in tests/ directory

### Outdated Scripts
- ❌ `scripts/check_active_adaptive.py` - References old "active_adaptive" API endpoint
- ❌ `scripts/verify_adapted_cycles.py` - May reference old adaptive scheduler

### Outdated Documentation
- ❌ `TEST_STATUS.md` - Outdated (tests have been updated)
- ❌ `UI_COMPATIBILITY.md` - Outdated (UI has been updated)
- ❌ `TEST_SUMMARY.md` - Outdated test summary

### Cache Files
- ❌ `__pycache__/` directories - Python bytecode cache (can be regenerated)

## Files Kept (Still Useful)

### Documentation
- ✅ `REFACTOR_STATUS.md` - Current status document
- ✅ `RUNTIME_TEST_STATUS.md` - Current runtime test status
- ✅ `TODO.md` - Future enhancements tracking
- ✅ `ADAPTATION_FEATURES.md` - Feature documentation
- ✅ `ADAPTIVE_FACTORS.md` - Factor documentation
- ✅ `ACTIVE_ADAPTIVE_DESIGN.md` - Design documentation (historical reference)

### Scripts
- ✅ `scripts/install_daemon.sh` - Still useful
- ✅ `scripts/uninstall_daemon.sh` - Still useful
- ✅ `scripts/prevent_sleep.sh` - Still useful
- ✅ `scripts/run_background.sh` - Still useful

## Cleanup Date
Cleanup performed on: 2024-12-29

## Summary

✅ **Removed 9 files:**
- 4 test scripts from `src/` directory (outdated config format)
- 2 outdated scripts from `scripts/` directory (old API endpoints)
- 3 outdated documentation files

✅ **Cleaned up:**
- All `__pycache__` directories (Python bytecode cache)

✅ **Files verified as already removed:**
- `src/scheduler.py` - Already removed
- `src/time_scheduler.py` - Already removed


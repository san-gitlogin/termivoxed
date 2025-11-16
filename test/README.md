# TermiVoxed Test Suite

This directory contains test utilities for TermiVoxed, particularly for validating TTS service connectivity and proxy configuration.

## Test Scripts

### `test_tts_service.py`

Comprehensive TTS service test utility that validates:
- Network connectivity (direct and proxy)
- Voice list retrieval
- Actual TTS generation (audio and subtitles)
- Performance measurements

#### Usage

**Full Test Suite:**
```bash
python3 test/test_tts_service.py
```

Runs all tests including:
- Connectivity test (direct and proxy)
- Voice list retrieval
- TTS generation with audio and subtitle validation

**Quick Connectivity Test Only:**
```bash
python3 test/test_tts_service.py --connectivity-only
```

Tests only network connectivity without generating any audio files.

**Verbose Mode:**
```bash
python3 test/test_tts_service.py --verbose
```

Enables detailed output including:
- Error tracebacks
- Subtitle content preview
- Additional debugging information

**Quick Mode (Skip TTS Generation):**
```bash
python3 test/test_tts_service.py --quick
```

Runs connectivity and voice listing tests but skips actual audio generation (faster).

#### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--verbose` | `-v` | Enable verbose output with detailed debugging |
| `--quick` | `-q` | Skip TTS generation test for faster execution |
| `--connectivity-only` | `-c` | Run connectivity test only |

#### Test Output

The test utility provides color-coded output with:
- ✅ Green for successful tests
- ❌ Red for failed tests
- ⏭️ Yellow for skipped tests
- ℹ️ Blue for informational messages
- ⚠️ Yellow for warnings

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed successfully |
| 1 | One or more tests failed |
| 130 | Tests interrupted by user (Ctrl+C) |

## Test Results

### What Gets Tested

1. **Service Initialization**
   - Configuration loading
   - TTS service instantiation
   - Proxy setting validation

2. **Connectivity Tests**
   - Direct connection to Microsoft Edge TTS servers
   - Proxy connection (if configured)
   - Connection timing and performance

3. **Voice List Retrieval**
   - Fetch available voices from TTS service
   - Validate voice data structure
   - Display sample voices

4. **TTS Generation** (unless `--quick` mode)
   - Generate test audio file
   - Generate test subtitle file
   - Validate file sizes and content
   - Measure generation performance

### Performance Metrics

The test utility measures and reports:
- Service initialization time
- Connectivity test duration
- Voice retrieval time
- Audio generation time
- Total test execution time

## Troubleshooting

### Test Fails with "Cannot reach TTS service"

**Possible Causes:**
1. No internet connection
2. Firewall blocking TTS servers
3. Incorrect proxy configuration
4. TTS service temporarily unavailable

**Solutions:**
1. Check your internet connection
2. Verify firewall settings
3. Review proxy configuration in `.env` file
4. Try again later if service is down

### Test Passes but TermiVoxed Fails

**Possible Causes:**
1. Timing issues (test uses short test text)
2. Different network paths for different requests
3. Proxy stability issues

**Solutions:**
1. Run test with `--verbose` for detailed logs
2. Check TermiVoxed logs in `logs/` directory
3. Try disabling/enabling proxy to compare

### Proxy Test Fails

**Possible Causes:**
1. Incorrect proxy URL format
2. Proxy authentication required
3. Proxy doesn't allow TTS connections
4. Proxy temporarily down

**Solutions:**
1. Verify proxy URL format: `http://host:port`
2. Add credentials if needed: `http://user:pass@host:port`
3. Contact your network administrator
4. Try direct connection (disable proxy)

## Examples

### Example 1: First Time Setup

```bash
# 1. Configure proxy in .env
nano .env

# 2. Run full test suite
python3 test/test_tts_service.py

# 3. If all tests pass, you're good to go!
python3 main.py
```

### Example 2: Debugging Connection Issues

```bash
# Run with verbose output to see detailed errors
python3 test/test_tts_service.py --verbose
```

### Example 3: Quick Proxy Check

```bash
# Just test connectivity without generating audio
python3 test/test_tts_service.py --connectivity-only
```

### Example 4: Performance Testing

```bash
# Run full suite and note the timing metrics
python3 test/test_tts_service.py

# Compare direct vs proxy performance
# 1. Disable proxy and test
TTS_PROXY_ENABLED=false python3 test/test_tts_service.py

# 2. Enable proxy and test
TTS_PROXY_ENABLED=true python3 test/test_tts_service.py
```

## Adding New Tests

To add new test functions to `test_tts_service.py`:

1. Create an async test function:
```python
async def test_new_feature(tts_service, verbose=False):
    """Test description"""
    print_section("🧪 Testing New Feature")
    # ... test implementation
    return {'success': True, 'details': {...}}
```

2. Add to main test flow:
```python
# In main() function
new_result = await test_new_feature(tts_service, args.verbose)
test_results['new_feature'] = new_result
```

3. Update summary section to include new test

## Files Generated During Tests

Test files are stored in the project's storage directory:
- **Audio:** `storage/projects/test_connectivity/en/connectivity_test.mp3`
- **Subtitles:** `storage/projects/test_connectivity/en/connectivity_test.srt`

These files are kept in cache and reused on subsequent runs (unless text or voice changes).

## Best Practices

1. **Always run tests after changing proxy configuration**
2. **Run with `--verbose` when debugging issues**
3. **Use `--connectivity-only` for quick network checks**
4. **Check logs directory for detailed error information**
5. **Run tests before reporting bugs to gather diagnostic info**

## Support

If tests fail consistently:
1. Save verbose test output: `python3 test/test_tts_service.py --verbose > test_results.txt 2>&1`
2. Check logs: `cat logs/termivoxed.log`
3. Review PROXY_SETUP.md for configuration guidance
4. File an issue with test results and configuration (without credentials)

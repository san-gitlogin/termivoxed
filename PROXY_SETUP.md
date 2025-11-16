# TTS Proxy Configuration Guide

This guide explains how to configure and use proxy support in TermiVoxed for accessing Microsoft Edge TTS service.

## Overview

TermiVoxed now supports HTTP/HTTPS proxy connections to reach Microsoft Edge TTS servers. This is particularly useful when:
- You're behind a corporate firewall
- Direct access to Microsoft Edge TTS servers is blocked
- You need to route TTS requests through a specific proxy server

## Features

- ✅ **Automatic Proxy Support**: Configure once, use everywhere
- ✅ **Fallback Mechanism**: Automatically tries direct connection if proxy fails
- ✅ **Connectivity Testing**: Built-in utility to test your proxy configuration
- ✅ **Status Logging**: Clear indication of which connection method is being used
- ✅ **Zero Breaking Changes**: Works seamlessly with existing projects

## Configuration

### Step 1: Edit `.env` File

Open the `.env` file in your TermiVoxed installation directory and configure the proxy settings:

```bash
# TTS Proxy Configuration (Optional)
# Set this if you're behind a corporate proxy and cannot reach Microsoft Edge TTS servers directly
# Format: http://proxy-server:port or https://proxy-server:port
# Example: http://proxy.company.com:8080
# Leave TTS_PROXY_ENABLED=false or TTS_PROXY_URL empty to connect directly without proxy
TTS_PROXY_ENABLED=true
TTS_PROXY_URL=http://your-proxy-server:port
```

### Configuration Options

| Setting | Description | Example |
|---------|-------------|---------|
| `TTS_PROXY_ENABLED` | Enable/disable proxy usage | `true` or `false` |
| `TTS_PROXY_URL` | Proxy server URL | `http://proxy.company.com:8080` |

### Example Configurations

#### Corporate Proxy
```bash
TTS_PROXY_ENABLED=true
TTS_PROXY_URL=http://proxy.corporate.com:8080
```

#### No Proxy (Direct Connection)
```bash
TTS_PROXY_ENABLED=false
TTS_PROXY_URL=
```

#### Proxy with Authentication
If your proxy requires authentication, include credentials in the URL:
```bash
TTS_PROXY_ENABLED=true
TTS_PROXY_URL=http://username:password@proxy.company.com:8080
```

## Testing Your Configuration

### Using the TTS Service Test Utility

TermiVoxed includes a comprehensive TTS service test utility to verify your proxy configuration and TTS functionality:

```bash
# Full test suite (connectivity, voice listing, TTS generation)
python3 test/test_tts_service.py

# Quick connectivity test only
python3 test/test_tts_service.py --connectivity-only

# Verbose output for debugging
python3 test/test_tts_service.py --verbose

# Quick mode (skip TTS generation)
python3 test/test_tts_service.py --quick
```

This utility will:
1. Display your current proxy configuration
2. Test direct connection to TTS service
3. Test proxy connection (if configured)
4. Test voice list retrieval
5. Test actual TTS generation (with audio and subtitle files)
6. Provide detailed recommendations based on the results
7. Display performance metrics and timing information

### Expected Output

```
================================================================================
            TermiVoxed - TTS Service Comprehensive Test
================================================================================

Test Started: 2025-01-16 10:30:45
Test Mode: Normal

Environment Information:
  Python Version: 3.11.5
  Platform: darwin
  Working Directory: /Users/user/termivoxed

────────────────────────────────────────────────────────────────────────────────
🚀 Initializing TTS Service
────────────────────────────────────────────────────────────────────────────────

ℹ️  Loading configuration and initializing TTS service...
  ✅ Service Initialization: SUCCESS (0.05s)

────────────────────────────────────────────────────────────────────────────────
🔍 Testing TTS Connectivity
────────────────────────────────────────────────────────────────────────────────

ℹ️  Testing connection to Microsoft Edge TTS service...
ℹ️  This may take 10-20 seconds...

Configuration:
  Proxy Enabled: True
  Proxy URL: http://your-proxy:8080

Connection Test Results:
  ❌ Direct Connection: FAILED
      ↳ Cannot reach TTS servers directly
  ✅ Proxy Connection: SUCCESS

Test Duration: 15.23 seconds

💡 Recommendation:
✅ Use proxy connection
ℹ️  Action: Keep TTS_PROXY_ENABLED=true in .env file

────────────────────────────────────────────────────────────────────────────────
📋 Testing Voice List Retrieval
────────────────────────────────────────────────────────────────────────────────

ℹ️  Fetching available voices from TTS service...

  ✅ Voice List Retrieval: SUCCESS (2.34s)
      ↳ Retrieved 450 voices

Sample Voices (first 10):
  1. Microsoft Server Speech Text to Speech Voice (en-US, Female)
  2. Microsoft Server Speech Text to Speech Voice (en-GB, Male)
  ...

────────────────────────────────────────────────────────────────────────────────
🎙️  Testing TTS Audio Generation
────────────────────────────────────────────────────────────────────────────────

ℹ️  Generating test audio file...
ℹ️  Test text: 'Hello, this is a test of the text-to-speech service.'

  ✅ Audio Generation: SUCCESS (3.45s)
      ↳ Audio file: connectivity_test.mp3 (45,678 bytes)
      ↳ Subtitle file: connectivity_test.srt (234 bytes)
      ↳ Voice: en-US-AvaMultilingualNeural
      ↳ Generation time: 3.45s

File Validation:
✅ Audio file size valid: 45,678 bytes
✅ Subtitle file size valid: 234 bytes

────────────────────────────────────────────────────────────────────────────────
📊 Test Summary
────────────────────────────────────────────────────────────────────────────────

Tests Completed:
  ✅ Connectivity: SUCCESS
  ✅ Voice Listing: SUCCESS
  ✅ TTS Generation: SUCCESS

Total Test Duration: 21.07 seconds

================================================================================
                          ✅ All Tests Passed!
================================================================================
✅ Your TTS service is properly configured and working!
```

## How It Works

### Automatic Fallback

TermiVoxed implements an intelligent fallback mechanism:

1. **Proxy Enabled**:
   - First tries to connect via proxy
   - If proxy fails, automatically falls back to direct connection
   - Logs which method succeeded

2. **Proxy Disabled**:
   - Uses direct connection only
   - No proxy overhead

### Connection Flow

```
User generates TTS
    ↓
Is proxy enabled and configured?
    ├─ Yes → Try proxy connection
    │   ├─ Success → Use proxy ✅
    │   └─ Failed → Try direct connection
    │       ├─ Success → Use direct ✅
    │       └─ Failed → Error ❌
    │
    └─ No → Try direct connection
        ├─ Success → Use direct ✅
        └─ Failed → Error ❌
```

### Logging and Status

TermiVoxed provides clear logging about proxy usage:

```
🌐 TTS Proxy ENABLED: http://your-proxy:8080
🌐 Using proxy mode with fallback: http://your-proxy:8080
✅ Generated audio via PROXY successfully
```

Or if using direct connection:
```
🌐 TTS Proxy DISABLED: Direct connection to TTS service
✅ Generated audio via DIRECT connection successfully
```

## Troubleshooting

### Problem: Cannot reach TTS service with or without proxy

**Solution:**
1. Run the connectivity test: `python3 test/test_tts_service.py --connectivity-only`
2. Check your network connection
3. Verify proxy URL is correct
4. Ensure firewall allows connections to Microsoft Edge TTS servers
5. Try disabling proxy temporarily: `TTS_PROXY_ENABLED=false`

### Problem: Proxy authentication required

**Solution:**
Include credentials in the proxy URL:
```bash
TTS_PROXY_URL=http://username:password@proxy.company.com:8080
```

**Security Note**: Be careful with credentials in `.env` file. Consider using environment variables or a secrets manager for production use.

### Problem: Slow TTS generation

**Solution:**
1. Run connectivity test to see which method is faster
2. If direct connection works, disable proxy: `TTS_PROXY_ENABLED=false`
3. Check proxy server performance
4. Consider using a faster proxy server

### Problem: Proxy works for some requests, fails for others

**Solution:**
This is normal behavior. The fallback mechanism will automatically use direct connection when proxy fails. Check logs to see which method is being used:

```bash
# View logs
tail -f logs/termivoxed.log
```

## Advanced Configuration

### Environment Variables

You can also configure proxy settings via environment variables:

```bash
export TTS_PROXY_ENABLED=true
export TTS_PROXY_URL=http://proxy.company.com:8080
python3 main.py
```

### Programmatic Configuration

If you're integrating TermiVoxed into your own application, you can configure proxy programmatically:

```python
from config import settings

# Update settings
settings.TTS_PROXY_ENABLED = True
settings.TTS_PROXY_URL = "http://proxy.company.com:8080"

# Create TTS service
from backend.tts_service import TTSService
tts_service = TTSService()

# Test connectivity
import asyncio
status = asyncio.run(tts_service.check_tts_connectivity())
print(status)
```

## Security Considerations

1. **Credentials in .env**: The `.env` file may contain proxy credentials. Ensure it's:
   - Not committed to version control (already in `.gitignore`)
   - Has restricted file permissions: `chmod 600 .env`

2. **Proxy Trust**: Only use trusted proxy servers. TTS requests contain your text content.

3. **HTTPS Proxies**: Prefer HTTPS proxies for encrypted proxy connections:
   ```bash
   TTS_PROXY_URL=https://proxy.company.com:443
   ```

## FAQ

### Q: Do I need to restart TermiVoxed after changing proxy settings?

**A:** Yes, changes to `.env` require restarting the application.

### Q: Will proxy affect TTS cache?

**A:** No, TTS cache works the same regardless of proxy settings. Cached results are returned immediately without any network connection.

### Q: Can I use SOCKS proxy?

**A:** Currently, only HTTP/HTTPS proxies are supported by edge-tts. SOCKS proxy support depends on the edge-tts library.

### Q: Does proxy work for voice list fetching?

**A:** The voice list API may use different endpoints. If you have issues, please file a bug report.

### Q: What happens if I set TTS_PROXY_ENABLED=true but don't set TTS_PROXY_URL?

**A:** The proxy will be disabled, and direct connection will be used. You'll see a warning in the logs.

## Support

If you encounter issues with proxy configuration:

1. Run the connectivity test utility
2. Check the logs in `logs/termivoxed.log`
3. File an issue on GitHub with:
   - Your proxy configuration (without credentials)
   - Connectivity test results
   - Relevant log excerpts

## Changelog

### Version 1.0.0 (Current)
- ✅ Initial proxy support implementation
- ✅ Automatic fallback mechanism
- ✅ Connectivity test utility
- ✅ Comprehensive logging
- ✅ Support for HTTP/HTTPS proxies
- ✅ Proxy authentication support

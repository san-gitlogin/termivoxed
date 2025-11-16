#!/usr/bin/env python3
"""
TTS Service Comprehensive Test Utility

This utility performs comprehensive testing of the TTS service including:
- Connectivity tests (direct and proxy)
- Actual TTS generation test
- Performance measurements
- Configuration validation

Run this script to verify your TTS setup and proxy configuration.

Usage:
    python3 test/test_tts_service.py
    python3 test/test_tts_service.py --verbose
    python3 test/test_tts_service.py --quick  # Skip actual TTS generation
"""

import asyncio
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
import tempfile
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.tts_service import TTSService
from utils.logger import logger
from config import settings

# ANSI color codes for better visual output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text, char="="):
    """Print a formatted header"""
    width = 80
    print()
    print(f"{Colors.BOLD}{Colors.HEADER}{char * width}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(width)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{char * width}{Colors.ENDC}")
    print()


def print_section(text):
    """Print a section header"""
    print()
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}")
    print()


def print_test(test_name, status, duration=None, details=None):
    """Print a test result"""
    if status == "success":
        symbol = f"{Colors.OKGREEN}✅{Colors.ENDC}"
        status_text = f"{Colors.OKGREEN}SUCCESS{Colors.ENDC}"
    elif status == "failed":
        symbol = f"{Colors.FAIL}❌{Colors.ENDC}"
        status_text = f"{Colors.FAIL}FAILED{Colors.ENDC}"
    elif status == "skipped":
        symbol = f"{Colors.WARNING}⏭️{Colors.ENDC}"
        status_text = f"{Colors.WARNING}SKIPPED{Colors.ENDC}"
    elif status == "running":
        symbol = f"{Colors.OKBLUE}🔄{Colors.ENDC}"
        status_text = f"{Colors.OKBLUE}RUNNING{Colors.ENDC}"
    else:
        symbol = "❓"
        status_text = "UNKNOWN"

    duration_text = f" ({duration:.2f}s)" if duration else ""
    print(f"  {symbol} {test_name}: {status_text}{duration_text}")

    if details:
        for detail in details:
            print(f"      {Colors.OKCYAN}↳{Colors.ENDC} {detail}")


def print_info(text):
    """Print an info message"""
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")


def print_success(text):
    """Print a success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_warning(text):
    """Print a warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_error(text):
    """Print an error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


async def test_connectivity(tts_service, verbose=False):
    """Test TTS connectivity"""
    print_section("🔍 Testing TTS Connectivity")

    print_info("Testing connection to Microsoft Edge TTS service...")
    print_info("This may take 10-20 seconds...")
    print()

    start_time = time.time()

    try:
        status = await tts_service.check_tts_connectivity()
        duration = time.time() - start_time

        # Display configuration
        print(f"{Colors.BOLD}Configuration:{Colors.ENDC}")
        print(f"  Proxy Enabled: {Colors.OKGREEN if status['proxy_enabled'] else Colors.WARNING}{status['proxy_enabled']}{Colors.ENDC}")
        print(f"  Proxy URL: {status['proxy_url'] or 'Not configured'}")
        print()

        # Display test results
        print(f"{Colors.BOLD}Connection Test Results:{Colors.ENDC}")

        # Direct connection test
        if status['direct_connection']:
            print_test("Direct Connection", "success")
        else:
            print_test("Direct Connection", "failed",
                      details=["Cannot reach TTS servers directly"])

        # Proxy connection test
        if status['proxy_enabled'] and status['proxy_url']:
            if status['proxy_connection']:
                print_test("Proxy Connection", "success")
            else:
                print_test("Proxy Connection", "failed",
                          details=[f"Cannot reach TTS servers via proxy: {status['proxy_url']}"])
        else:
            print_test("Proxy Connection", "skipped",
                      details=["Proxy not configured in .env file"])

        print()
        print(f"{Colors.BOLD}Test Duration:{Colors.ENDC} {duration:.2f} seconds")
        print()

        # Recommendations
        print(f"{Colors.BOLD}💡 Recommendation:{Colors.ENDC}")
        if status['recommended_mode'] == 'direct':
            print_success("Use direct connection (no proxy needed)")
            print_info("Action: Set TTS_PROXY_ENABLED=false in .env file")
        elif status['recommended_mode'] == 'proxy':
            print_success("Use proxy connection")
            print_info("Action: Keep TTS_PROXY_ENABLED=true in .env file")
        else:
            print_error("Cannot reach TTS service via any method!")
            print_warning("Possible issues:")
            print("      • Network connectivity problems")
            print("      • Firewall blocking TTS servers")
            print("      • Incorrect proxy configuration")
            print("      • TTS service temporarily unavailable")

        return status

    except Exception as e:
        duration = time.time() - start_time
        print_test("Connectivity Test", "failed", duration)
        print_error(f"Error: {str(e)}")
        return None


async def test_tts_generation(tts_service, verbose=False):
    """Test actual TTS generation"""
    print_section("🎙️  Testing TTS Audio Generation")

    print_info("Generating test audio file...")
    print_info("Test text: 'Hello, this is a test of the text-to-speech service.'")
    print()

    test_text = "Hello, this is a test of the text-to-speech service."
    test_voice = "en-US-AvaMultilingualNeural"

    start_time = time.time()

    try:
        # Create a temporary directory for test files
        with tempfile.TemporaryDirectory() as temp_dir:
            print_test("Audio Generation", "running")

            # Generate audio
            audio_path, subtitle_path = await tts_service.generate_audio(
                text=test_text,
                language="en",
                voice=test_voice,
                project_name="test_connectivity",
                segment_name="connectivity_test",
                rate="+0%",
                volume="+0%",
                pitch="+0Hz",
                orientation='horizontal'
            )

            duration = time.time() - start_time

            # Verify files exist
            audio_exists = os.path.exists(audio_path)
            subtitle_exists = os.path.exists(subtitle_path)

            details = []
            if audio_exists:
                audio_size = os.path.getsize(audio_path)
                details.append(f"Audio file: {os.path.basename(audio_path)} ({audio_size} bytes)")
            else:
                details.append("⚠️ Audio file not created")

            if subtitle_exists:
                subtitle_size = os.path.getsize(subtitle_path)
                details.append(f"Subtitle file: {os.path.basename(subtitle_path)} ({subtitle_size} bytes)")
            else:
                details.append("⚠️ Subtitle file not created")

            details.append(f"Voice: {test_voice}")
            details.append(f"Generation time: {duration:.2f}s")

            if audio_exists and subtitle_exists:
                print_test("Audio Generation", "success", duration, details)

                # Additional file validation
                print()
                print(f"{Colors.BOLD}File Validation:{Colors.ENDC}")

                if audio_size > 1000:  # At least 1KB
                    print_success(f"Audio file size valid: {audio_size:,} bytes")
                else:
                    print_warning(f"Audio file suspiciously small: {audio_size} bytes")

                if subtitle_size > 0:
                    print_success(f"Subtitle file size valid: {subtitle_size:,} bytes")
                else:
                    print_warning("Subtitle file is empty")

                # Read subtitle content
                if verbose:
                    print()
                    print(f"{Colors.BOLD}Generated Subtitle Content:{Colors.ENDC}")
                    with open(subtitle_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(f"{Colors.OKCYAN}{content}{Colors.ENDC}")

                return {
                    'success': True,
                    'audio_path': audio_path,
                    'subtitle_path': subtitle_path,
                    'audio_size': audio_size,
                    'subtitle_size': subtitle_size,
                    'duration': duration
                }
            else:
                print_test("Audio Generation", "failed", duration, details)
                return {'success': False}

    except Exception as e:
        duration = time.time() - start_time
        print_test("Audio Generation", "failed", duration,
                  details=[f"Error: {str(e)}"])

        if verbose:
            import traceback
            print()
            print(f"{Colors.BOLD}Error Traceback:{Colors.ENDC}")
            print(f"{Colors.FAIL}{traceback.format_exc()}{Colors.ENDC}")

        return {'success': False, 'error': str(e)}


async def test_voice_listing(tts_service, verbose=False):
    """Test fetching available voices"""
    print_section("📋 Testing Voice List Retrieval")

    print_info("Fetching available voices from TTS service...")
    print()

    start_time = time.time()

    try:
        voices = await tts_service.get_available_voices()
        duration = time.time() - start_time

        if voices and len(voices) > 0:
            print_test("Voice List Retrieval", "success", duration,
                      details=[f"Retrieved {len(voices)} voices"])

            # Show sample voices
            print()
            print(f"{Colors.BOLD}Sample Voices (first 10):{Colors.ENDC}")
            for i, voice in enumerate(voices[:10]):
                voice_name = voice.get('name', 'Unknown')
                locale = voice.get('locale', 'Unknown')
                gender = voice.get('gender', 'Unknown')
                print(f"  {i+1}. {voice_name} ({locale}, {gender})")

            if len(voices) > 10:
                print(f"  ... and {len(voices) - 10} more voices")

            return {'success': True, 'count': len(voices), 'duration': duration}
        else:
            print_test("Voice List Retrieval", "failed", duration,
                      details=["No voices returned from service"])
            return {'success': False}

    except Exception as e:
        duration = time.time() - start_time
        print_test("Voice List Retrieval", "failed", duration,
                  details=[f"Error: {str(e)}"])

        if verbose:
            import traceback
            print()
            print(f"{Colors.BOLD}Error Traceback:{Colors.ENDC}")
            print(f"{Colors.FAIL}{traceback.format_exc()}{Colors.ENDC}")

        return {'success': False, 'error': str(e)}


async def main():
    """Main test function"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='TTS Service Comprehensive Test Utility')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--quick', '-q', action='store_true',
                       help='Skip TTS generation test (faster)')
    parser.add_argument('--connectivity-only', '-c', action='store_true',
                       help='Run connectivity test only')
    args = parser.parse_args()

    # Print header
    print_header("TermiVoxed - TTS Service Comprehensive Test", "=")

    # Display timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Colors.BOLD}Test Started:{Colors.ENDC} {timestamp}")
    print(f"{Colors.BOLD}Test Mode:{Colors.ENDC} {'Verbose' if args.verbose else 'Normal'}")
    print()

    # Display environment info
    print(f"{Colors.BOLD}Environment Information:{Colors.ENDC}")
    print(f"  Python Version: {sys.version.split()[0]}")
    print(f"  Platform: {sys.platform}")
    print(f"  Working Directory: {os.getcwd()}")

    # Initialize test results
    test_results = {
        'connectivity': None,
        'voice_listing': None,
        'tts_generation': None
    }

    total_start_time = time.time()

    try:
        # Initialize TTS service
        print_section("🚀 Initializing TTS Service")
        print_info("Loading configuration and initializing TTS service...")

        init_start = time.time()
        tts_service = TTSService()
        init_duration = time.time() - init_start

        print_test("Service Initialization", "success", init_duration)

        # Test 1: Connectivity
        connectivity_result = await test_connectivity(tts_service, args.verbose)
        test_results['connectivity'] = connectivity_result

        if connectivity_result and connectivity_result.get('recommended_mode') == 'none':
            print_warning("Skipping further tests due to connectivity failure")
            return 1

        if args.connectivity_only:
            print_info("Connectivity-only mode: Skipping other tests")
        else:
            # Test 2: Voice Listing
            voice_result = await test_voice_listing(tts_service, args.verbose)
            test_results['voice_listing'] = voice_result

            # Test 3: TTS Generation (unless quick mode)
            if not args.quick:
                generation_result = await test_tts_generation(tts_service, args.verbose)
                test_results['tts_generation'] = generation_result
            else:
                print_section("🎙️  TTS Generation Test")
                print_test("Audio Generation", "skipped",
                          details=["Quick mode enabled (--quick)"])

        # Print summary
        total_duration = time.time() - total_start_time
        print_section("📊 Test Summary")

        print(f"{Colors.BOLD}Tests Completed:{Colors.ENDC}")

        # Connectivity summary
        if test_results['connectivity']:
            conn = test_results['connectivity']
            status = "success" if conn['recommended_mode'] != 'none' else "failed"
            print_test("Connectivity", status)

        # Voice listing summary
        if test_results['voice_listing']:
            status = "success" if test_results['voice_listing']['success'] else "failed"
            print_test("Voice Listing", status)
        elif args.connectivity_only:
            print_test("Voice Listing", "skipped")

        # TTS generation summary
        if test_results['tts_generation']:
            status = "success" if test_results['tts_generation']['success'] else "failed"
            print_test("TTS Generation", status)
        elif args.quick or args.connectivity_only:
            print_test("TTS Generation", "skipped")

        print()
        print(f"{Colors.BOLD}Total Test Duration:{Colors.ENDC} {total_duration:.2f} seconds")
        print()

        # Determine overall result
        connectivity_ok = test_results['connectivity'] and test_results['connectivity']['recommended_mode'] != 'none'
        voice_ok = test_results['voice_listing'] is None or test_results['voice_listing'].get('success', False)
        generation_ok = test_results['tts_generation'] is None or test_results['tts_generation'].get('success', False)

        if connectivity_ok and voice_ok and generation_ok:
            print_header("✅ All Tests Passed!", "=")
            print_success("Your TTS service is properly configured and working!")
            print()
            return 0
        else:
            print_header("⚠️  Some Tests Failed", "=")
            print_warning("Please review the test results above and check your configuration")
            print()
            return 1

    except KeyboardInterrupt:
        print()
        print_warning("Tests interrupted by user")
        return 130

    except Exception as e:
        print()
        print_error(f"Unexpected error during tests: {str(e)}")

        if args.verbose:
            import traceback
            print()
            print(f"{Colors.BOLD}Error Traceback:{Colors.ENDC}")
            print(f"{Colors.FAIL}{traceback.format_exc()}{Colors.ENDC}")

        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print(f"{Colors.WARNING}⚠️  Test interrupted by user{Colors.ENDC}")
        sys.exit(130)

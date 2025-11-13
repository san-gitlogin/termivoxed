#!/usr/bin/env python3
"""Test script to check edge-tts voices API and structure"""

import asyncio
import edge_tts
import json


async def test_voices():
    print("Testing edge-tts voices API...\n")

    # Test Method 1: VoicesManager (new API)
    try:
        print("Method 1: VoicesManager.create()")
        from edge_tts import VoicesManager
        voices_manager = await VoicesManager.create()
        voices = voices_manager.voices
        print(f"✓ SUCCESS: Got {len(voices)} voices using VoicesManager")

        if voices:
            print("\nFirst voice structure:")
            print(json.dumps(voices[0], indent=2))

            # Check for English voices
            en_voices = [v for v in voices if v.get('Locale', '').startswith('en')]
            print(f"\n✓ Found {len(en_voices)} English voices")

            if en_voices:
                print("\nFirst 3 English voices:")
                for i, v in enumerate(en_voices[:3], 1):
                    name = v.get('FriendlyName') or v.get('Name') or v.get('ShortName')
                    gender = v.get('Gender') or v.get('VoiceGender')
                    print(f"  {i}. {name} ({gender})")

        return voices

    except Exception as e:
        print(f"✗ FAILED: {e}")

    # Test Method 2: list_voices (old API)
    try:
        print("\nMethod 2: edge_tts.list_voices()")
        voices = await edge_tts.list_voices()
        print(f"✓ SUCCESS: Got {len(voices)} voices using list_voices()")

        if voices:
            print("\nFirst voice structure:")
            print(json.dumps(voices[0], indent=2))

        return voices

    except Exception as e:
        print(f"✗ FAILED: {e}")

    print("\n✗ ERROR: Could not fetch voices with any method!")
    return []


async def main():
    print("=" * 60)
    print("EDGE-TTS VOICES API TEST")
    print("=" * 60)

    voices = await test_voices()

    print("\n" + "=" * 60)
    if voices:
        print("✓ RESULT: Voice fetching works!")
        print(f"  Total voices: {len(voices)}")
    else:
        print("✗ RESULT: Voice fetching failed!")
        print("\n  Possible solutions:")
        print("  1. Update edge-tts: pip install --upgrade edge-tts")
        print("  2. Reinstall: pip uninstall edge-tts && pip install edge-tts")
        print("  3. Check your internet connection")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

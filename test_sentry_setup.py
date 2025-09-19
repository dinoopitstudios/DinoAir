"""
Simple test script to verify Sentry configuration.
Run this to test if Sentry is properly set up.
"""

import os
import sys

# Add the current directory to Python path so we can import the API
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Try to load environment variables
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Successfully loaded .env file")
except ImportError:
    print("ℹ️  python-dotenv not available, using system environment")

# Check for Sentry DSN
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    # Only show last 10 chars
    print(f"✅ Sentry DSN found: ***{sentry_dsn[-10:]}")
else:
    print("❌ No SENTRY_DSN environment variable found")

# Test Sentry SDK import
try:
    import sentry_sdk

    print("✅ sentry_sdk imported successfully")
    print(f"   Version: {sentry_sdk.VERSION}")

    # Test initialization
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn, send_default_pii=True, traces_sample_rate=1.0, environment="test"
        )
        print("✅ Sentry initialized successfully")

        # Test error capture
        try:
            1 / 0  # This will trigger a division by zero error
        except ZeroDivisionError as e:
            sentry_sdk.capture_exception(e)
            print("✅ Test error sent to Sentry")
            print("   Check your Sentry dashboard for the error!")

    else:
        print("⚠️  Cannot test Sentry without DSN")

except ImportError as e:
    print(f"❌ Could not import sentry_sdk: {e}")

print("\n" + "=" * 50)
print("Sentry Setup Test Complete")
print("=" * 50)

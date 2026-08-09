import aiohttp.streams

if not hasattr(aiohttp.streams, "AsyncStreamReaderMixin"):

	class AsyncStreamReaderMixin:
		pass

	aiohttp.streams.AsyncStreamReaderMixin = AsyncStreamReaderMixin

import os

import frappe
import vcr

CASSETTE_DIR = os.path.join(os.path.dirname(__file__), "integrations", "cassettes")

# Determine record mode based on whether real credentials are provided
has_credentials = bool(frappe.conf.get("apollo_test_account") or os.environ.get("APOLLO_TEST_ACCOUNT"))
record_mode = "once" if has_credentials else "none"

# Configure VCR to scrub sensitive headers
my_vcr = vcr.VCR(
	cassette_library_dir=CASSETTE_DIR,
	record_mode=record_mode,
	filter_headers=["Authorization", "X-Api-Key"],
)

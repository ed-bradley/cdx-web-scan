from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BarcodeValidationResult:
	ok: bool
	value: str | None = None
	error: str | None = None


def normalize_barcode(raw: str | None) -> str:
	if not raw:
		return ""
	return "".join(raw.split())


def validate_upc_ean(raw: str | None) -> BarcodeValidationResult:
	value = normalize_barcode(raw)
	if not value:
		return BarcodeValidationResult(ok=False, error="Enter a UPC/EAN code.")
	if not value.isdigit():
		return BarcodeValidationResult(ok=False, error="UPC/EAN must contain digits only.")

	# Common lengths: EAN-8 (8), UPC-A (12), EAN-13 (13), ITF-14 (14)
	if not (8 <= len(value) <= 14):
		return BarcodeValidationResult(
			ok=False,
			error="UPC/EAN length must be 8–14 digits.",
		)

	return BarcodeValidationResult(ok=True, value=value)

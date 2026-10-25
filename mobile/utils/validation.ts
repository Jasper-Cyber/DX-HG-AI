/**
 * Care-profile form validation. Pure + testable (Task 27).
 *
 * The care profile is entirely optional (Req 10.1), so empty fields are valid.
 * Validation only rejects clearly malformed entries and enforces that an
 * emergency contact, if added, has at least a name and phone.
 */
import type { CareProfile, EmergencyContact } from "@/api/types";

export interface FieldErrors {
  phone?: string;
  defaultLat?: string;
  defaultLon?: string;
  contacts: Record<number, { name?: string; phone?: string }>;
}

/** Loose phone check: optional +, digits, spaces, dashes, parens; 6-20 chars. */
export function isValidPhone(phone: string): boolean {
  const trimmed = phone.trim();
  if (trimmed === "") return true; // optional
  return /^\+?[\d\s().-]{6,20}$/.test(trimmed);
}

/** A latitude in [-90, 90]; blank is allowed. */
export function isValidLat(value: string): boolean {
  if (value.trim() === "") return true;
  const n = Number(value);
  return Number.isFinite(n) && n >= -90 && n <= 90;
}

/** A longitude in [-180, 180]; blank is allowed. */
export function isValidLon(value: string): boolean {
  if (value.trim() === "") return true;
  const n = Number(value);
  return Number.isFinite(n) && n >= -180 && n <= 180;
}

export function validateContact(c: EmergencyContact): { name?: string; phone?: string } {
  const errs: { name?: string; phone?: string } = {};
  if (!c.name || c.name.trim() === "") errs.name = "Name is required";
  if (!c.phone || c.phone.trim() === "") errs.phone = "Phone is required";
  else if (!isValidPhone(c.phone)) errs.phone = "Enter a valid phone number";
  return errs;
}

/** Validate the whole profile; returns per-field errors (empty => valid). */
export function validateCareProfile(profile: CareProfile): FieldErrors {
  const errors: FieldErrors = { contacts: {} };

  if (profile.phone && !isValidPhone(profile.phone)) {
    errors.phone = "Enter a valid phone number";
  }
  if (profile.defaultLat !== undefined && !isValidLat(String(profile.defaultLat))) {
    errors.defaultLat = "Latitude must be between -90 and 90";
  }
  if (profile.defaultLon !== undefined && !isValidLon(String(profile.defaultLon))) {
    errors.defaultLon = "Longitude must be between -180 and 180";
  }

  profile.emergencyContacts.forEach((c, i) => {
    const errs = validateContact(c);
    if (errs.name || errs.phone) errors.contacts[i] = errs;
  });

  return errors;
}

/** True when a FieldErrors object has no errors. */
export function hasNoErrors(errors: FieldErrors): boolean {
  return (
    !errors.phone &&
    !errors.defaultLat &&
    !errors.defaultLon &&
    Object.keys(errors.contacts).length === 0
  );
}

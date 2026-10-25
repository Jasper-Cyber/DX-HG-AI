import type { CareProfile } from "@/api/types";
import {
  hasNoErrors,
  isValidLat,
  isValidLon,
  isValidPhone,
  validateCareProfile,
  validateContact,
} from "@/utils/validation";

describe("field validators", () => {
  it("treats blank optional fields as valid", () => {
    expect(isValidPhone("")).toBe(true);
    expect(isValidLat("")).toBe(true);
    expect(isValidLon("")).toBe(true);
  });

  it("accepts well-formed phones and rejects junk", () => {
    expect(isValidPhone("+1 (555) 123-4567")).toBe(true);
    expect(isValidPhone("abc")).toBe(false);
    expect(isValidPhone("12")).toBe(false);
  });

  it("bounds latitude and longitude", () => {
    expect(isValidLat("45")).toBe(true);
    expect(isValidLat("91")).toBe(false);
    expect(isValidLon("-180")).toBe(true);
    expect(isValidLon("181")).toBe(false);
  });
});

describe("validateContact", () => {
  it("requires name and phone", () => {
    const errs = validateContact({ name: "", phone: "", priority: 1 });
    expect(errs.name).toBeDefined();
    expect(errs.phone).toBeDefined();
  });

  it("passes a complete contact", () => {
    const errs = validateContact({ name: "Jo", phone: "555-1234", priority: 1 });
    expect(errs.name).toBeUndefined();
    expect(errs.phone).toBeUndefined();
  });
});

describe("validateCareProfile", () => {
  it("accepts an empty profile (all optional)", () => {
    const profile: CareProfile = { emergencyContacts: [] };
    expect(hasNoErrors(validateCareProfile(profile))).toBe(true);
  });

  it("flags a bad phone and a bad contact", () => {
    const profile: CareProfile = {
      phone: "xx",
      emergencyContacts: [{ name: "", phone: "", priority: 1 }],
    };
    const errors = validateCareProfile(profile);
    expect(errors.phone).toBeDefined();
    expect(errors.contacts[0]).toBeDefined();
    expect(hasNoErrors(errors)).toBe(false);
  });
});

import { AppHeader } from "@/components/AppHeader";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";

import type { CareProfile, EmergencyContact } from "@/api/types";
import {
  useCareProfile,
  useSettings,
  useUpdateCareProfile,
  useUpdateSettings,
} from "@/api/hooks";
import { FeatureToggleRow } from "@/components/FeatureToggleRow";
import { LabeledInput } from "@/components/LabeledInput";
import { SimulatedDataRibbon } from "@/components/SimulatedDataRibbon";
import { hasNoErrors, validateCareProfile, type FieldErrors } from "@/utils/validation";
import { theme } from "@/theme";

const EMPTY_PROFILE: CareProfile = { emergencyContacts: [] };

/**
 * Settings / Care profile (Task 22, Req 10.1, 10.2, 11.1).
 *
 * Optional personal details + emergency contacts + default location + preferred
 * doctor id, persisted via useCareProfile. Feature toggles for warnings /
 * suggestions / emergency (suggestions + emergency default OFF). Links to the
 * experimental disclaimer. Everything here is optional; the app works with it
 * empty/disabled.
 */
export default function ProfileScreen() {
  const careQuery = useCareProfile();
  const updateProfile = useUpdateCareProfile();
  const settings = useSettings();
  const updateSettings = useUpdateSettings();

  const [form, setForm] = useState<CareProfile>(EMPTY_PROFILE);
  const [errors, setErrors] = useState<FieldErrors>({ contacts: {} });

  // Seed the form once the profile loads.
  useEffect(() => {
    if (careQuery.data) setForm(careQuery.data);
  }, [careQuery.data]);

  const setField = <K extends keyof CareProfile>(key: K, value: CareProfile[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const setContact = (i: number, patch: Partial<EmergencyContact>) =>
    setForm((f) => ({
      ...f,
      emergencyContacts: f.emergencyContacts.map((c, idx) => (idx === i ? { ...c, ...patch } : c)),
    }));

  const addContact = () =>
    setForm((f) => ({
      ...f,
      emergencyContacts: [
        ...f.emergencyContacts,
        { name: "", phone: "", priority: f.emergencyContacts.length + 1 },
      ],
    }));

  const removeContact = (i: number) =>
    setForm((f) => ({
      ...f,
      emergencyContacts: f.emergencyContacts.filter((_, idx) => idx !== i),
    }));

  const onSave = () => {
    const found = validateCareProfile(form);
    setErrors(found);
    if (hasNoErrors(found)) updateProfile.mutate(form);
  };

  const s = settings.data;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <SimulatedDataRibbon />
      <AppHeader title="Settings" />
      <ScrollView contentContainerStyle={styles.content}>


        {/* Care profile */}
        <Text style={styles.sectionLabel}>Care profile (optional)</Text>
        <View style={styles.card}>
          <LabeledInput
            label="Your name"
            value={form.fullName ?? ""}
            onChangeText={(t) => setField("fullName", t || undefined)}
            placeholder="e.g. Demo User"
          />
          <LabeledInput
            label="Your phone"
            value={form.phone ?? ""}
            onChangeText={(t) => setField("phone", t || undefined)}
            placeholder="optional"
            keyboardType="phone-pad"
            error={errors.phone}
          />
          <View style={styles.rowTwo}>
            <View style={styles.flex1}>
              <LabeledInput
                label="Default latitude"
                value={form.defaultLat !== undefined ? String(form.defaultLat) : ""}
                onChangeText={(t) => setField("defaultLat", t === "" ? undefined : Number(t))}
                placeholder="optional"
                keyboardType="numbers-and-punctuation"
                error={errors.defaultLat}
              />
            </View>
            <View style={styles.flex1}>
              <LabeledInput
                label="Default longitude"
                value={form.defaultLon !== undefined ? String(form.defaultLon) : ""}
                onChangeText={(t) => setField("defaultLon", t === "" ? undefined : Number(t))}
                placeholder="optional"
                keyboardType="numbers-and-punctuation"
                error={errors.defaultLon}
              />
            </View>
          </View>
          <LabeledInput
            label="Preferred doctor ID"
            value={form.preferredProviderId !== undefined ? String(form.preferredProviderId) : ""}
            onChangeText={(t) =>
              setField("preferredProviderId", t === "" ? undefined : Number(t))
            }
            placeholder="optional — pick from providers"
            keyboardType="number-pad"
          />
        </View>

        {/* Emergency contacts */}
        <Text style={styles.sectionLabel}>Emergency contacts (optional)</Text>
        <View style={styles.card}>
          {form.emergencyContacts.length === 0 ? (
            <Text style={styles.muted}>No contacts added.</Text>
          ) : (
            form.emergencyContacts.map((c, i) => (
              <View key={i} style={styles.contact}>
                <LabeledInput
                  label="Name"
                  value={c.name}
                  onChangeText={(t) => setContact(i, { name: t })}
                  error={errors.contacts[i]?.name}
                />
                <LabeledInput
                  label="Relationship"
                  value={c.relationship ?? ""}
                  onChangeText={(t) => setContact(i, { relationship: t || undefined })}
                  placeholder="optional"
                />
                <LabeledInput
                  label="Phone"
                  value={c.phone}
                  onChangeText={(t) => setContact(i, { phone: t })}
                  keyboardType="phone-pad"
                  error={errors.contacts[i]?.phone}
                />
                <Pressable onPress={() => removeContact(i)} accessibilityRole="button">
                  <Text style={styles.remove}>Remove</Text>
                </Pressable>
              </View>
            ))
          )}
          <Pressable style={styles.addBtn} onPress={addContact} accessibilityRole="button">
            <Text style={styles.addBtnText}>+ Add contact</Text>
          </Pressable>
        </View>

        <Pressable
          style={[styles.save, updateProfile.isPending && styles.saveDisabled]}
          onPress={onSave}
          disabled={updateProfile.isPending}
          accessibilityRole="button"
        >
          <Text style={styles.saveText}>
            {updateProfile.isPending ? "Saving…" : "Save care profile"}
          </Text>
        </Pressable>
        {updateProfile.isSuccess ? <Text style={styles.savedOk}>Saved.</Text> : null}
        {updateProfile.isError ? (
          <Text style={styles.saveErr}>Couldn’t save. Check the backend and try again.</Text>
        ) : null}

        {/* Feature toggles */}
        <Text style={styles.sectionLabel}>Features</Text>
        <View style={styles.card}>
          <FeatureToggleRow
            label="Monitoring warnings"
            description="Show trend-review and attention warnings."
            value={s?.warningsEnabled ?? true}
            disabled={!s || updateSettings.isPending}
            onValueChange={(v) => updateSettings.mutate({ warningsEnabled: v })}
          />
          <FeatureToggleRow
            label="Nearby provider suggestions"
            description="Suggest nearby providers on a warning. Off by default."
            value={s?.suggestionsEnabled ?? false}
            disabled={!s || updateSettings.isPending}
            onValueChange={(v) => updateSettings.mutate({ suggestionsEnabled: v })}
          />
          <FeatureToggleRow
            label="Emergency response"
            description="Enable the opt-in emergency dispatch flow. Off by default."
            value={s?.emergencyEnabled ?? false}
            disabled={!s || updateSettings.isPending}
            onValueChange={(v) => updateSettings.mutate({ emergencyEnabled: v })}
          />
        </View>

        {/* Disclaimer access */}
        <Pressable
          style={styles.linkRow}
          onPress={() => router.push("/disclaimer?mode=view")}
          accessibilityRole="button"
        >
          <Text style={styles.linkText}>View experimental disclaimer</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.bg },
  content: { padding: theme.spacing(4), paddingTop: 4, paddingBottom: 28, gap: theme.spacing(3) },
  h1: { color: theme.colors.textPrimary, fontFamily: theme.type.heading, fontSize: theme.font.h1, fontWeight: "700" },
  sectionLabel: {
    color: theme.colors.textSecondary,
    fontFamily: theme.type.mono, fontSize: theme.font.caption,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginTop: theme.spacing(1),
  },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing(4),
    gap: theme.spacing(3),
  },
  rowTwo: { flexDirection: "row", gap: theme.spacing(3) },
  flex1: { flex: 1 },
  contact: {
    gap: theme.spacing(2),
    paddingBottom: theme.spacing(3),
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  remove: { color: theme.colors.danger, fontFamily: theme.type.mono, fontSize: theme.font.caption, fontWeight: "600" },
  addBtn: { paddingVertical: theme.spacing(2), alignItems: "center" },
  addBtnText: { color: theme.colors.accent, fontFamily: theme.type.body, fontSize: theme.font.body, fontWeight: "700" },
  muted: { color: theme.colors.textSecondary, fontFamily: theme.type.body, fontSize: theme.font.body },
  save: {
    backgroundColor: theme.colors.accent,
    borderRadius: theme.radius.md,
    paddingVertical: theme.spacing(3),
    alignItems: "center",
  },
  saveDisabled: { opacity: 0.5 },
  saveText: { color: theme.colors.onAccent, fontWeight: "800", fontFamily: theme.type.body, fontSize: theme.font.body },
  savedOk: { color: theme.colors.accentGreen, fontFamily: theme.type.mono, fontSize: theme.font.caption },
  saveErr: { color: theme.colors.danger, fontFamily: theme.type.mono, fontSize: theme.font.caption },
  linkRow: { paddingVertical: theme.spacing(3), alignItems: "center" },
  linkText: { color: theme.colors.experimental, fontFamily: theme.type.body, fontSize: theme.font.body, fontWeight: "600" },
});

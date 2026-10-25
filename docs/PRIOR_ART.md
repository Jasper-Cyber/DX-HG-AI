# Prior Art — Wearable Fall and Cardiovascular Notifications

The summaries below are paraphrased and are included to frame the MVP as an implementation experiment, not a novelty or medical-device claim.

## Apple Watch Fall Detection

Apple documents a fall-detection flow in which a detected hard fall can prompt the wearer, allow an emergency call, and—when the wearer remains immobile for about one minute—start a 30-second countdown before automatically calling emergency services. The watch can then notify configured emergency contacts and share location information.

- Source: [Apple Support — Use Fall Detection with Apple Watch](https://support.apple.com/en-us/HT208944)
- Accessed: 2026-10-25

## Smartwatch cardiovascular notifications

The FDA describes post-market evaluation of cardiovascular notifications from consumer smartwatches. The page identifies Apple, Samsung, and Fitbit wearables as providing atrial-fibrillation notifications and examines how such notifications perform after deployment.

- Source: [FDA — Post-market Evaluation of Smartwatch Cardiovascular Notifications](https://www.fda.gov/science-research/advancing-regulatory-science/post-market-evaluation-smartwatch-cardiovascular-notifications)
- Accessed: 2026-10-25

## MVP relationship and talking points

- Established products already demonstrate fall-based prompts/escalation and wearable AF notifications.
- This MVP does not claim to be first, novel, clinically validated, diagnostic, or a medical device.
- The experiment combines an AF-like ECG rhythm score with motion reliability/corroboration in one deterministic escalation decision.
- Heavy motion downgrades paired ECG rather than strengthening an alert; Watch requires K-of-N reliable ECG windows, and Warning requires motion corroboration.
- A process-local cancel/countdown loop demonstrates human control. Only simulated text/state escalation exists; no request, notification, or dispatch is sent.
- ECG and motion windows come from different public datasets and different people, and there is no paired actual stroke-onset evidence.

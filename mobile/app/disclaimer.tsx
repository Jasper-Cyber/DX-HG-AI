import { router, useLocalSearchParams } from "expo-router";

import { useAckDisclaimer, useSettings } from "@/api/hooks";
import { DisclaimerModal } from "@/components/DisclaimerModal";

/**
 * Experimental disclaimer route (Task 23, Req 12).
 *
 * Two modes via the `mode` param:
 *  - "view" (from Settings): read-only, no acknowledge button.
 *  - default (first-launch gate): shows the acknowledge button; recording the
 *    acknowledgement dismisses the modal.
 */
export default function DisclaimerScreen() {
  const params = useLocalSearchParams<{ mode?: string }>();
  const readOnly = params.mode === "view";

  const settings = useSettings();
  const ack = useAckDisclaimer();

  const onAcknowledge = () => {
    ack.mutate(undefined, {
      onSuccess: () => dismiss(),
      // Even if the backend is unreachable, let the user proceed rather than
      // trapping them behind an un-dismissable modal; the ack will be retried
      // next launch when settings load.
      onError: () => dismiss(),
    });
  };

  return (
    <DisclaimerModal
      showAck={!readOnly}
      onAcknowledge={onAcknowledge}
      acknowledging={ack.isPending || settings.isLoading}
    />
  );
}

function dismiss() {
  if (router.canGoBack()) router.back();
  else router.replace("/(tabs)");
}

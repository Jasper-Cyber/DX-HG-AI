import { useState } from "react";
import type { SelectableChartPointProps } from "./SelectableChartPoint";

/** DOM SVG needs browser events, not React Native's responder handlers. */
export function SelectableChartPoint({ label, selected, onSelect, ...shape }: SelectableChartPointProps) {
  const [focused, setFocused] = useState(false);
  return <circle {...shape} role="button" tabIndex={0} aria-label={label} aria-pressed={selected}
    onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
    strokeWidth={focused ? 3 : selected ? 2 : 1}
    style={{ cursor: "pointer", outline: focused ? "2px solid #182922" : undefined, outlineOffset: 3 }} onClick={onSelect}
    onKeyDown={event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onSelect();
      }
    }} />;
}

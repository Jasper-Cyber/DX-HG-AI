import { Circle } from "react-native-svg";

export interface SelectableChartPointProps {
  cx: number;
  cy: number;
  r: number;
  fill: string;
  stroke: string;
  label: string;
  selected: boolean;
  onSelect: () => void;
}

/** Native SVG uses the responder system for touch selection. */
export function SelectableChartPoint({ label, selected, onSelect, ...shape }: SelectableChartPointProps) {
  return <Circle {...shape} accessible accessibilityLabel={label} onPress={onSelect} />;
}

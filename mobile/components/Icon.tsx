import Svg, { Circle, Path } from "react-native-svg";
import { theme } from "@/theme";
export type IconName = "heart" | "pulse" | "drop" | "moon" | "activity" | "shield" | "sparkles" | "chart" | "sliders" | "settings" | "user" | "clock" | "play" | "pause" | "reset" | "chevron" | "info" | "check" | "alert";
const paths: Record<IconName, string> = {
  heart: "M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z",
  pulse: "M2 12h5l3-8 4 16 3-8h5",
  drop: "M12 2S5 10 5 14a7 7 0 0 0 14 0c0-4-7-12-7-12ZM8 14a4 4 0 0 0 4 4",
  moon: "M20.8 14A9 9 0 0 1 10 3.2 9 9 0 1 0 20.8 14Z",
  activity: "M13 6l-3 5 4 3-1 7M10 11l-4 2M13 6l3 5h4M10 15l-4 6",
  shield: "M12 2l8 4v6c0 5-8 10-8 10S4 17 4 12V6l8-4Z",
  sparkles: "m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2ZM20 2v4M18 4h4",
  chart: "M4 20v-5M10 20V9M16 20V5M22 20V2M3 10l6-6 5 2 7-5",
  sliders: "M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6",
  settings: "m9 3 1-2h4l1 2 2 1 2-1 2 3-1 2v3l2 1-1 4-2 1-2 2v2h-4l-1-2-2-1-2 1-2-3 1-2v-3L2 9l1-4 2-1 2 1 2-2Z",
  user: "M20 21v-2a6 6 0 0 0-6-6h-4a6 6 0 0 0-6 6v2Z",
  clock: "M12 6v6l4 2",
  play: "m8 4 12 8-12 8V4Z",
  pause: "M8 4v16M16 4v16",
  reset: "M3 10a9 9 0 1 1 1 8M3 3v7h7",
  chevron: "m9 5 7 7-7 7",
  info: "M12 11v6M12 7h.01",
  check: "m5 12 4 4L19 6",
  alert: "M12 8v5M12 17h.01M12 2 2 21h20L12 2Z",
};
export function Icon({ name, size = 20, color = theme.colors.accent }: { name: IconName; size?: number; color?: string }) {
  return <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
    <Path d={paths[name]} />
    {name === "user" && <Circle cx={12} cy={6} r={3} />}
    {(name === "clock" || name === "info") && <Circle cx={12} cy={12} r={9} />}
    {name === "settings" && <Circle cx={12} cy={11} r={3} />}
    {name === "activity" && <Circle cx={15} cy={3} r={1.4} />}
  </Svg>;
}

import { useId } from "react";
import Svg, { Circle, Defs, LinearGradient, Stop, Path } from "react-native-svg";
interface MiniTrendProps { values: (number | null)[]; color: string; height?: number }
/** Missing and low-quality samples keep their positions and break the trace. */
export function MiniTrend({ values, color, height = 40 }: MiniTrendProps) {
  const id = "trend" + useId().replace(/:/g, "");
  const usable = values.filter((v): v is number => v !== null && Number.isFinite(v));
  if (!usable.length) return null;
  const min = Math.min(...usable), max = Math.max(...usable);
  const x = (i: number) => values.length === 1 ? 100 : i * 200 / (values.length - 1);
  const y = (v: number) => max === min ? height / 2 : height - 5 - (v - min) / (max - min) * (height - 10);
  let drawing = false;
  const path = values.map((v, i) => {
    if (v === null || !Number.isFinite(v)) { drawing = false; return ""; }
    const command = `${drawing ? "L" : "M"}${x(i)},${y(v)}`;
    drawing = true;
    return command;
  }).join(" ");
  return <Svg width="100%" height={height} viewBox={`0 0 200 ${height}`} preserveAspectRatio="none">
    <Defs><LinearGradient id={id} x1="0" y1="0" x2="0" y2="1"><Stop offset="0" stopColor={color} stopOpacity={.16} /><Stop offset="1" stopColor={color} stopOpacity={0} /></LinearGradient></Defs>
    {usable.length === values.length && values.length > 1 && <Path d={`${path} L200,${height} L0,${height} Z`} fill={`url(#${id})`} />}
    <Path d={path} fill="none" stroke={color} strokeWidth={1.8} vectorEffect="non-scaling-stroke" />
    {values.map((v, i) => v !== null && Number.isFinite(v) && (i === values.length - 1 || (values[i - 1] == null && values[i + 1] == null)) ? <Circle key={i} cx={x(i)} cy={y(v)} r={2} fill={color} /> : null)}
  </Svg>;
}

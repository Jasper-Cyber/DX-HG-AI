/** @jest-environment jsdom */
import { createRoot } from "react-dom/client";
import { act } from "react-dom/test-utils";
import { SelectableChartPoint } from "@/components/SelectableChartPoint.web";

it("renders a DOM circle without responder warnings and supports mouse and keyboard selection", () => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  const errors = jest.spyOn(console, "error").mockImplementation(() => {});
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const onSelect = jest.fn();
  try {
    act(() => root.render(<svg><SelectableChartPoint cx={10} cy={10} r={5} fill="orange"
      stroke="black" label="VO2 sample" selected={false} onSelect={onSelect} /></svg>));
    const point = container.querySelector("circle");
    expect(point.getAttribute("aria-label")).toBe("VO2 sample");
    expect(point.getAttribute("tabindex")).toBe("0");
    act(() => point.dispatchEvent(new MouseEvent("click", { bubbles: true })));
    act(() => point.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true })));
    act(() => point.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true })));
    expect(onSelect).toHaveBeenCalledTimes(3);
    expect(errors.mock.calls).toEqual([]);
  } finally {
    act(() => root.unmount());
    container.remove();
    errors.mockRestore();
  }
});

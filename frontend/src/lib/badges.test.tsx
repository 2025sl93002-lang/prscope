import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SeverityBadge, Badge } from "../components/ui";
import { UsageBadge, UpdateBadge } from "./badges";

describe("status badges", () => {
  it("renders a severity label (not color-only)", () => {
    render(<SeverityBadge severity="critical" />);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("renders usage status with a textual label", () => {
    render(<UsageBadge status="none" />);
    expect(screen.getByText("No usage found")).toBeInTheDocument();
  });

  it("renders an update type label", () => {
    render(<UpdateBadge type="major" />);
    expect(screen.getByText("Major")).toBeInTheDocument();
  });

  it("renders a plain badge", () => {
    render(<Badge tone="ok">Healthy</Badge>);
    expect(screen.getByText("Healthy")).toBeInTheDocument();
  });
});

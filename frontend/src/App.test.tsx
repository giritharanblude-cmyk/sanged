import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders landing page with five module cards", () => {
    render(<App />);
    const cards = ["Payslip", "Bills", "Inventory", "Employees", "Company"];
    cards.forEach((name) => {
      expect(screen.getByText(name)).toBeInTheDocument();
    });
  });
});

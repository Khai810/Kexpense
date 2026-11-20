import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "../page";

describe("HomePage", () => {
  it("renders Kexpense headline and features", () => {
    render(<HomePage />);
    expect(screen.getByText("Kexpense")).toBeInTheDocument();
    expect(screen.getByText(/Smart Expense OCR v1.0/i)).toBeInTheDocument();
    expect(screen.getByText(/Quét Hóa Đơn Ngay/i)).toBeInTheDocument();
    expect(screen.getByText(/Bóc Tách Từng Món/i)).toBeInTheDocument();
  });
});

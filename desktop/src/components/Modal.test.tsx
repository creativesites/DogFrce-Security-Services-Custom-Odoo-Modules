// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { Modal } from "./Modal";

afterEach(cleanup);

function Harness({ onClose = () => {} }: { onClose?: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>open</button>
      {open && (
        <Modal title="Report a problem" onClose={() => { onClose(); setOpen(false); }}>
          <input aria-label="Summary" />
        </Modal>
      )}
    </>
  );
}

describe("Modal", () => {
  it("is a labelled dialog and moves focus into it", () => {
    render(<Harness />);
    fireEvent.click(screen.getByText("open"));
    const dialog = screen.getByRole("dialog", { name: "Report a problem" });
    expect(dialog).toBeTruthy();
    expect(dialog.contains(document.activeElement)).toBe(true);
  });

  it("closes on Escape and returns focus to what opened it", () => {
    const onClose = vi.fn();
    render(<Harness onClose={onClose} />);
    const opener = screen.getByText("open");
    opener.focus();
    fireEvent.click(opener);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(opener);
  });

  it("does not close while busy", () => {
    const onClose = vi.fn();
    render(<Modal title="Sending" busy onClose={onClose}><p>…</p></Modal>);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
  });
});

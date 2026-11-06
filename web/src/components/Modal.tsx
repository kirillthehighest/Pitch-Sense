// A dialog opened over the screen as the platform's own modal (Phase 25): it takes the keyboard's
// focus and keeps it inside, Escape closes it, and a click on the dimmed backdrop too.
import { type ReactNode, useEffect, useRef } from "react";

interface Props {
  label: string;
  onClose: () => void;
  children: ReactNode;
}

export function Modal({ label, onClose, children }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (typeof element.showModal === "function") element.showModal();
    else element.setAttribute("open", ""); // a browser (or test DOM) without modal dialogs
    return () => {
      if (typeof element.close === "function") element.close();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className="modal"
      aria-label={label}
      onCancel={(event) => {
        event.preventDefault(); // the screen closes it, so its state stays in one place
        onClose();
      }}
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      {children}
    </dialog>
  );
}

from __future__ import annotations

import tkinter as tk

from ppc_app.gui import PPCAnalyzerApp


def main() -> None:
    root = tk.Tk()
    PPCAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

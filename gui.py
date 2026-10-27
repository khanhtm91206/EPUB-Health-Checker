
"""
gui.py

Tkinter GUI for EPUB Health Checker.

Features:
- Select one EPUB or a directory
- Recursive directory scanning
- Select checkers individually
- Background scanning
- Progress bar
- PASS / FAIL / NO_RESULT summary
- Per-book results and checker details
- Compact problem-EPUB CSV/TXT export (no automatic detailed reports)

The existing CLI, Engine and main.py are not modified.
"""

from __future__ import annotations

import csv
import queue
import threading
import time
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cli import build_registry
from engine.scanner import Scanner
from engine.runner import Runner, ScanControl


class EPUBHealthGUI(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("EPUB Health Checker")
        self.geometry("1100x760")
        self.minsize(850, 580)

        self.registry = build_registry()
        self.scanner = Scanner()

        self.events = queue.Queue()
        self.worker = None
        self.batch_result = None
        self.scan_control = None
        self._scan_total = 0
        self._books_by_id = {}
        self._sort_key = "name"
        self._sort_reverse = False
        self._filter_after_id = None
        self._scan_started_at = None
        self._last_progress_time = 0.0

        self.path_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.scan_mode_var = tk.StringVar(value="zip")
        self._last_scan_mode = "zip"
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="ALL")
        self.readability_filter_var = tk.StringVar(value="ALL")
        self.visible_count_var = tk.StringVar(value="Showing 0 / 0 EPUBs")

        self.checker_vars = {
            name: tk.BooleanVar(value=True)
            for name in self.registry.names()
        }

        self._build_ui()
        self.scan_mode_var.trace_add("write", self._update_checker_controls)
        self._update_checker_controls()
        self.after(100, self._process_events)

    # --------------------------------------------------
    # UI construction
    # --------------------------------------------------

    def _build_ui(self):

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Web-like scrolling for the complete GUI.
        self.page_canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.page_scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.page_canvas.yview
        )
        self.page_canvas.configure(yscrollcommand=self.page_scrollbar.set)
        self.page_canvas.grid(row=0, column=0, sticky="nsew")
        self.page_scrollbar.grid(row=0, column=1, sticky="ns")

        root = ttk.Frame(self.page_canvas, padding=15)
        self._page_window = self.page_canvas.create_window(
            (0, 0), window=root, anchor="nw"
        )
        root.bind("<Configure>", self._update_page_scrollregion)
        self.page_canvas.bind("<Configure>", self._resize_page_width)

        root.columnconfigure(0, weight=1)
        # Results have their own useful height; the page itself scrolls.
        root.rowconfigure(3, weight=0)
        root.rowconfigure(4, weight=0)

        title = ttk.Label(
            root,
            text="EPUB Health Checker",
            font=("Segoe UI", 20, "bold"),
        )
        title.grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 15),
        )

        self._build_source_section(root)
        self._build_options_section(root)
        self._build_progress_section(root)
        self._build_results_section(root)
        # Canvas receives wheel events anywhere in the window, except the
        # independently scrollable results and checker details widgets.
        self.bind_all("<MouseWheel>", self._page_mousewheel)
        self.bind_all("<Button-4>", self._page_linuxwheel)
        self.bind_all("<Button-5>", self._page_linuxwheel)
        self.tree.bind("<MouseWheel>", self._tree_mousewheel)
        self.details.bind("<MouseWheel>", self._details_mousewheel)

    def _update_page_scrollregion(self, _event=None):
        self.page_canvas.configure(scrollregion=self.page_canvas.bbox("all"))

    def _resize_page_width(self, event):
        self.page_canvas.itemconfigure(self._page_window, width=event.width)

    def _page_mousewheel(self, event):
        # On Windows, event.delta is usually +/-120 per wheel notch.
        steps = -int(event.delta / 120) if event.delta else 0
        if steps == 0 and event.delta:
            steps = -1 if event.delta > 0 else 1
        if steps:
            self.page_canvas.yview_scroll(steps * 3, "units")
        return "break"

    def _page_linuxwheel(self, event):
        self.page_canvas.yview_scroll(-3 if event.num == 4 else 3, "units")
        return "break"

    def _tree_mousewheel(self, event):
        steps = -int(event.delta / 120) if event.delta else 0
        if steps == 0 and event.delta:
            steps = -1 if event.delta > 0 else 1
        if steps:
            self.tree.yview_scroll(steps * 3, "units")
        return "break"

    def _details_mousewheel(self, event):
        steps = -int(event.delta / 120) if event.delta else 0
        if steps == 0 and event.delta:
            steps = -1 if event.delta > 0 else 1
        if steps:
            first, last = self.details.yview()
            # If text is at the edge, continue scrolling the main page.
            if (steps < 0 and first <= 0) or (steps > 0 and last >= 1):
                self.page_canvas.yview_scroll(steps * 3, "units")
            else:
                self.details.yview_scroll(steps * 3, "units")
        return "break"

    def _build_source_section(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="EPUB Source",
            padding=12,
        )
        frame.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 10),
        )

        frame.columnconfigure(0, weight=1)

        ttk.Entry(
            frame,
            textvariable=self.path_var,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )

        ttk.Button(
            frame,
            text="Select EPUB",
            command=self._select_file,
        ).grid(row=0, column=1, padx=3)

        ttk.Button(
            frame,
            text="Select Folder",
            command=self._select_folder,
        ).grid(row=0, column=2, padx=3)

        ttk.Checkbutton(
            frame,
            text="Scan subfolders recursively",
            variable=self.recursive_var,
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(10, 0),
        )

    def _build_options_section(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Scan Options",
            padding=12,
        )
        frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 10),
        )

        frame.columnconfigure(0, weight=1)

        checker_frame = ttk.Frame(frame)
        checker_frame.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        ttk.Label(
            checker_frame,
            text="Checkers",
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        self.checker_buttons = []
        for index, (name, var) in enumerate(
            self.checker_vars.items()
        ):
            row = index // 4 + 1
            column = index % 4

            checkbox = ttk.Checkbutton(
                checker_frame,
                text=name,
                variable=var,
            )
            self.checker_buttons.append(checkbox)
            checkbox.grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 18),
                pady=3,
            )

        button_frame = ttk.Frame(frame)
        button_frame.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(12, 0),
        )

        self.select_all_button = ttk.Button(
            button_frame,
            text="Select All",
            command=lambda: self._set_checkers(True),
        )
        self.select_all_button.pack(side="left", padx=(0, 8))

        self.clear_all_button = ttk.Button(
            button_frame,
            text="Clear All",
            command=lambda: self._set_checkers(False),
        )
        self.clear_all_button.pack(side="left")

        mode_frame = ttk.LabelFrame(frame, text="Scan Mode", padding=8)
        mode_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for mode, description in (
            ("zip", "ZIP Integrity — verify ALL ZIP entries / CRC (recommended for damaged EPUBs)"),
            ("fast", "Fast Readability — sample up to 5 chapters (NOT full CRC)"),
            ("full", "Full Validation — full CRC + all chapters + selected checkers"),
        ):
            ttk.Radiobutton(
                mode_frame, text=description, variable=self.scan_mode_var, value=mode
            ).pack(anchor="w", pady=2)

        self.scan_button = ttk.Button(
            frame,
            text="Start Scan",
            command=self._start_scan,
        )
        self.scan_button.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(15, 0),
        )

        controls = ttk.Frame(frame)
        controls.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        for column in range(3):
            controls.columnconfigure(column, weight=1)
        self.pause_button = ttk.Button(
            controls, text="Pause", command=self._pause_scan, state="disabled"
        )
        self.pause_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.resume_button = ttk.Button(
            controls, text="Resume", command=self._resume_scan, state="disabled"
        )
        self.resume_button.grid(row=0, column=1, sticky="ew", padx=5)
        self.stop_button = ttk.Button(
            controls, text="Stop", command=self._stop_scan, state="disabled"
        )
        self.stop_button.grid(row=0, column=2, sticky="ew", padx=(5, 0))

    def _build_progress_section(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Progress",
            padding=12,
        )
        frame.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 10),
        )

        frame.columnconfigure(0, weight=1)

        ttk.Progressbar(
            frame,
            variable=self.progress_var,
            maximum=100,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
        )

        ttk.Label(
            frame,
            textvariable=self.status_var,
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

    def _build_results_section(self, parent):
        """Resizable results area: EPUB list above checker details."""
        frame = ttk.LabelFrame(parent, text="Scan Results", padding=8)
        frame.grid(row=4, column=0, sticky="nsew")
        parent.rowconfigure(4, weight=0, minsize=560)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # A draggable sash separates the two sections. Unlike two grid rows,
        # the details Text widget cannot force the EPUB table to height zero.
        self.results_pane = ttk.Panedwindow(frame, orient="vertical", height=560)
        self.results_pane.grid(row=0, column=0, sticky="nsew")

        table_frame = ttk.Frame(self.results_pane)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(table_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="Search:").grid(row=0, column=0, padx=(0, 6))
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Label(toolbar, text="Health:").grid(row=0, column=2, padx=(0, 5))
        status_box = ttk.Combobox(
            toolbar, textvariable=self.status_filter_var,
            values=("ALL", "HEALTHY", "WARNING", "ERROR", "CORRUPTED", "NOT_CHECKED"),
            state="readonly", width=12,
        )
        status_box.grid(row=0, column=3, padx=(0, 10))
        ttk.Label(toolbar, text="Readability:").grid(row=0, column=4, padx=(0, 5))
        readability_box = ttk.Combobox(
            toolbar, textvariable=self.readability_filter_var,
            values=("ALL", "READABLE", "UNREADABLE", "UNKNOWN"),
            state="readonly", width=13,
        )
        readability_box.grid(row=0, column=5, padx=(0, 10))
        ttk.Label(toolbar, textvariable=self.visible_count_var).grid(row=0, column=6)

        # Export only books requiring immediate attention, independently of filters.
        ttk.Button(
            toolbar,
            text="Export Problem EPUBs (CSV/TXT)",
            command=self._export_problem_epubs,
        ).grid(row=1, column=0, columnspan=7, sticky="w", pady=(8, 2))

        self.search_var.trace_add("write", self._schedule_filter)
        status_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_filter())
        readability_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_filter())

        self.tree = ttk.Treeview(
            table_frame,
            columns=("readability", "health", "status", "checks", "errors", "warnings", "path"),
            show="tree headings", selectmode="browse", height=6,
        )
        for column, title in (
            ("#0", "EPUB"), ("readability", "Readability"), ("health", "Health"), ("status", "Legacy"),
            ("checks", "Checks"), ("errors", "Errors"),
            ("warnings", "Warnings"), ("path", "Path"),
        ):
            self.tree.heading(
                column, text=title,
                command=lambda col=column: self._sort_by(col),
            )
        self.tree.column("#0", width=230, minwidth=120)
        self.tree.column("readability", width=125, minwidth=100, anchor="center")
        self.tree.column("health", width=110, minwidth=85, anchor="center")
        self.tree.column("status", width=80, minwidth=65, anchor="center")
        self.tree.column("checks", width=65, minwidth=55, anchor="center")
        self.tree.column("errors", width=65, minwidth=55, anchor="center")
        self.tree.column("warnings", width=80, minwidth=65, anchor="center")
        self.tree.column("path", width=400, minwidth=140)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        self.tree.tag_configure("HEALTHY", foreground="#15803d")
        self.tree.tag_configure("WARNING", foreground="#a16207")
        self.tree.tag_configure("ERROR", foreground="#dc2626")
        self.tree.tag_configure("CORRUPTED", foreground="#991b1b")
        self.tree.tag_configure("NOT_CHECKED", foreground="#64748b")
        self.tree.tag_configure("PASS", foreground="#15803d")
        self.tree.tag_configure("FAIL", foreground="#dc2626")
        self.tree.tag_configure("NO_RESULT", foreground="#64748b")
        self.tree.bind("<<TreeviewSelect>>", self._show_details)

        details_frame = ttk.LabelFrame(
            self.results_pane, text="Checker Details", padding=5
        )
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)

        self.details = tk.Text(
            details_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
            height=16,
        )
        self.details.grid(row=0, column=0, sticky="nsew")
        detail_scrollbar = ttk.Scrollbar(
            details_frame, orient="vertical", command=self.details.yview
        )
        detail_scrollbar.grid(row=0, column=1, sticky="ns")
        self.details.configure(yscrollcommand=detail_scrollbar.set)

        self.results_pane.add(table_frame, weight=3)
        self.results_pane.add(details_frame, weight=2)

    # --------------------------------------------------
    # Source selection
    # --------------------------------------------------

    def _select_file(self):

        path = filedialog.askopenfilename(
            title="Select EPUB",
            filetypes=[
                ("EPUB Files", "*.epub"),
                ("All Files", "*.*"),
            ],
        )

        if path:
            self.path_var.set(path)

    def _select_folder(self):

        path = filedialog.askdirectory(
            title="Select EPUB Folder",
        )

        if path:
            self.path_var.set(path)

    def _update_checker_controls(self, *_args):
        """Only Full Validation uses the optional checker selection.

        Keep the BooleanVar values intact so selections are restored when
        switching back to Full Validation.
        """
        state = "normal" if self.scan_mode_var.get() == "full" else "disabled"
        for checkbox in self.checker_buttons:
            checkbox.configure(state=state)
        self.select_all_button.configure(state=state)
        self.clear_all_button.configure(state=state)

    def _set_checkers(self, enabled: bool):

        for var in self.checker_vars.values():
            var.set(enabled)

    # --------------------------------------------------
    # Scan lifecycle
    # --------------------------------------------------

    def _pause_scan(self):
        if self.scan_control and not self.scan_control.is_stopped:
            self.scan_control.pause()
            self.pause_button.configure(state="disabled")
            self.resume_button.configure(state="normal")
            self.status_var.set("Pause requested — waiting for current EPUB to finish...")

    def _resume_scan(self):
        if self.scan_control and not self.scan_control.is_stopped:
            self.scan_control.resume()
            self.pause_button.configure(state="normal")
            self.resume_button.configure(state="disabled")
            self.status_var.set("Scanning resumed...")

    def _stop_scan(self):
        if self.scan_control:
            self.scan_control.stop()
            self.pause_button.configure(state="disabled")
            self.resume_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.status_var.set("Stop requested — finishing current EPUB...")

    def _finish_controls(self):
        self.scan_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")

    def _start_scan(self):

        if self.worker is not None and self.worker.is_alive():
            return

        path_text = self.path_var.get().strip()

        if not path_text:
            messagebox.showwarning(
                "Missing Source",
                "Please select an EPUB or folder.",
            )
            return

        source = Path(path_text).expanduser()

        if not source.exists():
            messagebox.showerror(
                "Invalid Source",
                f"Path does not exist:\n{source}",
            )
            return

        selected_checkers = [
            name
            for name, var in self.checker_vars.items()
            if var.get()
        ]

        scan_mode = self.scan_mode_var.get()
        if not selected_checkers and scan_mode == "full":
            messagebox.showwarning(
                "No Checkers",
                "Select at least one checker.",
            )
            return

        self._last_scan_mode = scan_mode
        self.batch_result = None
        self.scan_control = ScanControl()
        self._scan_total = 0
        self._scan_started_at = time.monotonic()
        self._books_by_id = {}
        self.search_var.set("")
        self.status_filter_var.set("ALL")
        self.readability_filter_var.set("ALL")
        self.visible_count_var.set("Showing 0 / 0 EPUBs")
        self.progress_var.set(0)
        self.status_var.set("Discovering EPUB files...")

        for item in self.tree.get_children():
            self.tree.delete(item)

        self._set_details("")
        self.scan_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        self.worker = threading.Thread(
            target=self._scan_worker,
            args=(
                source,
                self.recursive_var.get(),
                selected_checkers,
                scan_mode,
            ),
            daemon=True,
        )
        self.worker.start()

    def _scan_worker(
        self,
        source: Path,
        recursive: bool,
        selected_checkers: list[str],
        scan_mode: str,
    ):
        try:
            print("[DEBUG] Worker started", flush=True)
            print(f"[DEBUG] Source: {source}", flush=True)

            jobs = self.scanner.scan(
                source,
                recursive=recursive,
            )

            print(f"[DEBUG] Scanner found {len(jobs)} EPUBs", flush=True)

            if not jobs:
                self.events.put(("empty", "No EPUB files found."))
                return

            self.events.put(("discovered", len(jobs)))

            runner = Runner(self.registry)

            print("[DEBUG] Runner starting", flush=True)

            # Throttle frequent progress updates: important for 3,000+ EPUBs.
            # The runner still checks every file; only GUI notifications are limited.
            last_sent = [0.0, -1]

            def progress_callback(snapshot):
                now = time.monotonic()
                completed = snapshot.completed
                total = snapshot.total
                if (
                    completed != total
                    and completed != 0
                    and now - last_sent[0] < 0.15
                ):
                    return
                if completed == last_sent[1]:
                    return
                last_sent[0] = now
                last_sent[1] = completed
                self.events.put((
                    "progress",
                    (completed, total, snapshot.percent),
                ))

            batch = runner.run_batch(
                jobs,
                checker_names=selected_checkers,
                progress_callback=progress_callback,
                control=self.scan_control,
                fast_readability=(scan_mode == "fast"),
                zip_integrity=(scan_mode == "zip"),
            )

            print("[DEBUG] Runner finished", flush=True)

            self.events.put(("result", batch))

            self.events.put(("done", self.scan_control.is_stopped))

        except Exception:
            import traceback
            traceback.print_exc()
            self.events.put(("error", traceback.format_exc()))

    # --------------------------------------------------
    # Thread-safe UI events
    # --------------------------------------------------

    
    def _process_events(self):
        """
        Process background-worker events on the Tkinter main thread.

        Always schedule the next poll, even when an event handler
        raises an exception.
        """
        import traceback

        try:
            processed = 0

            # Limit work per UI tick to keep the window responsive.
            while processed < 100:
                try:
                    event, payload = self.events.get_nowait()
                except queue.Empty:
                    break

                processed += 1
                print(f"[GUI EVENT] {event}", flush=True)

                try:
                    if event == "discovered":
                        self._scan_total = payload
                        self.status_var.set(
                            f"Found {payload} EPUB files. Scanning..."
                        )

                    elif event == "progress":
                        completed, total, percent = payload

                        self.progress_var.set(percent)
                        elapsed = (
                            time.monotonic() - self._scan_started_at
                            if self._scan_started_at is not None else 0
                        )
                        elapsed_text = self._format_duration(elapsed)
                        if completed > 0 and completed < total:
                            remaining = elapsed / completed * (total - completed)
                            eta_text = f" | ETA ~{self._format_duration(remaining)}"
                        else:
                            eta_text = ""
                        if self.scan_control and self.scan_control.is_stopped:
                            self.status_var.set("Stopping — finishing current EPUB...")
                        elif self.scan_control and self.scan_control.is_paused:
                            self.status_var.set(
                                f"Pause requested / paused: {completed}/{total} | "
                                f"Elapsed {elapsed_text}"
                            )
                        else:
                            self.status_var.set(
                                f"Scanning: {completed}/{total} "
                                f"({percent:.1f}%) | Elapsed {elapsed_text}{eta_text}"
                            )

                    elif event == "result":
                        self.batch_result = payload
                        self._populate_results(payload)

                        self.status_var.set(
                            f"Received results for "
                            f"{len(payload.results)} EPUB(s)"
                        )

                    elif event == "empty":
                        self.status_var.set(payload)
                        self._finish_controls()

                        messagebox.showinfo(
                            "No EPUB Files",
                            payload,
                        )

                    elif event == "done":
                        stopped = bool(payload)
                        self._finish_controls()
                        if not stopped:
                            self.progress_var.set(100)

                        if self.batch_result is not None:
                            batch = self.batch_result

                            passed = sum(
                                book.status == "PASS"
                                for book in batch.results
                            )

                            failed = sum(
                                book.status == "FAIL"
                                for book in batch.results
                            )

                            no_result = sum(
                                book.status == "NO_RESULT"
                                for book in batch.results
                            )

                            elapsed = (
                                time.monotonic() - self._scan_started_at
                                if self._scan_started_at is not None else 0
                            )
                            health_summary = {}
                            for book in batch.results:
                                health_summary[book.health_status] = (
                                    health_summary.get(book.health_status, 0) + 1
                                )
                            readability_summary = {"READABLE": 0, "UNREADABLE": 0, "UNKNOWN": 0}
                            for book in batch.results:
                                readability_summary[book.readability_status] = (
                                    readability_summary.get(book.readability_status, 0) + 1
                                )
                            readability_text = " | ".join(
                                f"{name}: {readability_summary.get(name, 0)}"
                                for name in ("READABLE", "UNREADABLE", "UNKNOWN")
                            )
                            health_text = " | ".join(
                                f"{name}: {health_summary.get(name, 0)}"
                                for name in ("HEALTHY", "WARNING", "ERROR", "CORRUPTED", "NOT_CHECKED")
                            )
                            self.status_var.set(
                                ({"fast": "FAST SAMPLE (partial) | ", "zip": "FULL ZIP CRC CHECK (content not checked) | ", "full": "FULL VALIDATION | "}.get(self._last_scan_mode, "")) +
                                f"{'Stopped' if stopped else 'Completed'}: "
                                f"{batch.total}/{self._scan_total} EPUBs | "
                                f"PASS: {passed} | "
                                f"FAIL: {failed} | "
                                f"NO_RESULT: {no_result} | "
                                f"{readability_text} | {health_text} | Time: {self._format_duration(elapsed)}"
                            )

                    elif event == "error":
                        self._finish_controls()
                        self.status_var.set("Scan failed")

                        messagebox.showerror(
                            "Scan Error",
                            str(payload),
                        )

                except Exception:
                    error = traceback.format_exc()

                    print(
                        "[GUI EVENT ERROR]\n" + error,
                        flush=True,
                    )

                    self.status_var.set(
                        f"GUI error while processing: {event}"
                    )

                    self._finish_controls()

        except Exception:
            print(
                "[GUI POLLING ERROR]\n"
                + traceback.format_exc(),
                flush=True,
            )

        finally:
            # Crucial: keep polling even if an event handler fails.
            self.after(100, self._process_events)


    @staticmethod
    def _format_duration(seconds):
        seconds = max(0, int(seconds))
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}h {minutes:02d}m {secs:02d}s"
        if minutes:
            return f"{minutes}m {secs:02d}s"
        return f"{secs}s"

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    @staticmethod
    def _severity_counts(book):
        errors = 0
        warnings = 0
        for result in book.results:
            severity = getattr(result, "severity", "")
            severity = str(getattr(severity, "value", severity)).upper()
            if severity in ("ERROR", "CRITICAL"):
                errors += 1
            elif severity == "WARNING":
                warnings += 1
        return errors, warnings

    def _populate_results(self, batch):
        self._books_by_id = {}
        self.tree.delete(*self.tree.get_children())

        for index, book in enumerate(batch.results):
            item_id = str(index)
            self._books_by_id[item_id] = book
            errors, warnings = self._severity_counts(book)
            self.tree.insert(
                "", "end", iid=item_id, text=book.path.name,
                values=(
                    book.readability_status, book.health_status, book.status, len(book.results), errors, warnings,
                    str(book.path),
                ),
                tags=(book.health_status,),
            )

        self._apply_filter()

    def _schedule_filter(self, *_args):
        # Debounce typing so large libraries don't redraw on every keystroke.
        if self._filter_after_id is not None:
            self.after_cancel(self._filter_after_id)
        self._filter_after_id = self.after(180, self._apply_filter)

    def _sort_by(self, column):
        key = "name" if column == "#0" else column
        if self._sort_key == key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_key = key
            self._sort_reverse = False
        self._apply_filter()

    def _apply_filter(self):
        self._filter_after_id = None
        if not self._books_by_id:
            self.visible_count_var.set("Showing 0 / 0 EPUBs")
            return

        search = self.search_var.get().casefold().strip()
        status_filter = self.status_filter_var.get()
        readability_filter = self.readability_filter_var.get()
        matches = []
        for item_id, book in self._books_by_id.items():
            if status_filter != "ALL" and book.health_status != status_filter:
                continue
            if readability_filter != "ALL" and book.readability_status != readability_filter:
                continue
            if search and search not in book.path.name.casefold():
                continue
            matches.append(item_id)

        def sort_value(item_id):
            book = self._books_by_id[item_id]
            errors, warnings = self._severity_counts(book)
            values = {
                "name": book.path.name.casefold(),
                "readability": book.readability_status,
                "health": book.health_status,
                "status": book.status,
                "checks": len(book.results),
                "errors": errors,
                "warnings": warnings,
                "path": str(book.path).casefold(),
            }
            return values.get(self._sort_key, values["name"])

        matches.sort(key=sort_value, reverse=self._sort_reverse)
        selected = set(self.tree.selection())
        # Detach filtered-out rows without destroying them.
        for item_id in self._books_by_id:
            self.tree.detach(item_id)
        for position, item_id in enumerate(matches):
            self.tree.move(item_id, "", position)

        if not selected.intersection(matches):
            self._set_details("")
        self.visible_count_var.set(
            f"Showing {len(matches)} / {len(self._books_by_id)} EPUBs"
        )

    def _export_problem_epubs(self):
        """Export a compact, unique list of EPUBs requiring attention.

        Export is independent of search and table filters.
        No full checker report is generated automatically.
        """
        if self.batch_result is None:
            messagebox.showinfo("No scan results", "Run a scan before exporting.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Select problem EPUB categories")
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.grab_set()
        panel = ttk.Frame(dialog, padding=16)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Include EPUBs matching any selected category:").pack(anchor="w", pady=(0, 8))
        choices = {
            "CORRUPTED": tk.BooleanVar(master=dialog, value=True),
            "ERROR": tk.BooleanVar(master=dialog, value=True),
            "WARNING": tk.BooleanVar(master=dialog, value=False),
            "UNREADABLE": tk.BooleanVar(master=dialog, value=True),
            "UNKNOWN": tk.BooleanVar(master=dialog, value=self._last_scan_mode != "zip"),
        }
        for label, variable in choices.items():
            ttk.Checkbutton(panel, text=label, variable=variable).pack(anchor="w", pady=2)
        ttk.Label(panel, text="Each EPUB is exported once, regardless of matching categories.").pack(anchor="w", pady=(8, 12))
        selected = []

        def confirm():
            selected.extend(key for key, var in choices.items() if var.get())
            dialog.destroy()

        buttons = ttk.Frame(panel)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Export...", command=confirm).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.wait_window(dialog)
        if not selected:
            return

        health_categories = {"CORRUPTED", "ERROR", "WARNING"} & set(selected)
        readability_categories = {"UNREADABLE", "UNKNOWN"} & set(selected)
        problem_books = [
            book for book in self.batch_result.results
            if book.health_status in health_categories
            or book.readability_status in readability_categories
        ]
        if not problem_books:
            messagebox.showinfo("No matching EPUBs", "No EPUBs match the selected categories.")
            return

        output = filedialog.asksaveasfilename(
            title="Export problem EPUB list",
            defaultextension=".csv",
            initialfile="problem_epubs.csv",
            filetypes=[
                ("CSV file (Excel compatible)", "*.csv"),
                ("Text file (one path per line)", "*.txt"),
            ],
        )
        if not output:
            return

        destination = Path(output)
        try:
            if destination.suffix.lower() == ".txt":
                with destination.open("w", encoding="utf-8") as handle:
                    for book in problem_books:
                        handle.write(str(book.path) + "\n")
            elif destination.suffix.lower() == ".csv":
                with destination.open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow([
                        "EPUB", "Full Path", "Readability", "Health",
                        "Legacy Status", "Errors", "Warnings", "Readability Reason",
                        "First Issue",
                    ])
                    for book in problem_books:
                        errors, warnings = self._severity_counts(book)
                        first_issue = ""
                        for result in book.results:
                            severity = getattr(result, "severity", "")
                            severity = str(getattr(severity, "value", severity)).upper()
                            if severity in ("CRITICAL", "ERROR", "WARNING"):
                                first_issue = f"[{severity}] {result.checker}: {result.message or ''}"
                                break
                        # Keep exports small even when one EPUB produces thousands of findings.
                        first_issue = first_issue.replace("\r", " ").replace("\n", " ")[:300]
                        reason = ("Not assessed: ZIP integrity only; full CRC verified if no integrity errors"
                                  if self._last_scan_mode == "zip" and book.readability_status == "UNKNOWN"
                                  else str(book.readability_reason or ""))
                        reason = reason.replace("\r", " ").replace("\n", " ")[:300]
                        writer.writerow([
                            book.path.name, str(book.path), book.readability_status,
                            book.health_status, book.status, errors, warnings,
                            reason, first_issue,
                        ])
            else:
                messagebox.showerror("Unsupported format", "Choose a .csv or .txt file.")
                return
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return

        messagebox.showinfo(
            "Export completed",
            f"Exported {len(problem_books)} EPUB(s) to:\n{destination}",
        )

    def _show_details(self, event=None):

        selected = self.tree.selection()

        if not selected:
            return

        book = self._books_by_id.get(selected[0])

        if book is None:
            return

        lines = [
            f"EPUB: {book.path}",
            f"READABILITY: {book.readability_status}" + (" (NOT CHECKED — ZIP INTEGRITY ONLY)" if self._last_scan_mode == "zip" else " (FAST SAMPLE — NOT FULLY VERIFIED)" if self._last_scan_mode == "fast" else ""),
            f"READABILITY REASON: {book.readability_reason}",
            f"HEALTH: {book.health_status}",
            f"LEGACY STATUS: {book.status}",
            f"CHECKER RESULTS: {len(book.results)}",
            "",
            "=" * 65,
        ]

        for result in book.results:
            severity = result.severity

            if hasattr(severity, "value"):
                severity = severity.value

            lines.extend([
                f"Checker : {result.checker}",
                f"Status  : {'PASS' if result.success else 'FAIL'}",
                f"Severity: {severity}",
                f"Message : {result.message or '-'}",
            ])

            if result.file:
                lines.append(f"File    : {result.file}")

            if result.location:
                lines.append(
                    f"Location: {result.location}"
                )

            lines.extend([
                "-" * 65,
                "",
            ])

        self._set_details("\n".join(lines))

    def _set_details(self, content: str):

        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", content)
        self.details.yview_moveto(0)
        self.details.configure(state="disabled")


def main():
    app = EPUBHealthGUI()
    app.mainloop()


if __name__ == "__main__":
    main()


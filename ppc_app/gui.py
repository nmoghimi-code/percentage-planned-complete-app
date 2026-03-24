from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .analyzer import ActualizedActivityDetail, AnalysisResult, analyze_schedules
from .xer_parser import parse_xer_file


class PPCAnalyzerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Percentage Planned Complete")
        self.root.geometry("1180x840")
        self.root.minsize(1024, 720)

        self.previous_path_var = tk.StringVar()
        self.current_path_var = tk.StringVar()
        self.previous_data_date_var = tk.StringVar(value="Previous Data Date: -")
        self.current_data_date_var = tk.StringVar(value="Current Data Date: -")
        self.status_var = tk.StringVar(value="Select the previous and current XER files, then run the analysis.")

        self.starts_tree: ttk.Treeview | None = None
        self.finishes_tree: ttk.Treeview | None = None
        self.actualized_planned_start_tree: ttk.Treeview | None = None
        self.actualized_unplanned_start_tree: ttk.Treeview | None = None
        self.actualized_planned_finish_tree: ttk.Treeview | None = None
        self.actualized_unplanned_finish_tree: ttk.Treeview | None = None
        self.chart_canvas: FigureCanvasTkAgg | None = None
        self.chart_figure: Figure | None = None

        self._build_layout()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.root, padding=16)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Previous Schedule (.xer)").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(controls, textvariable=self.previous_path_var).grid(row=0, column=1, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(controls, text="Browse", command=self._choose_previous_file).grid(row=0, column=2, pady=(0, 8))

        ttk.Label(controls, text="Current Schedule (.xer)").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(controls, textvariable=self.current_path_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(controls, text="Browse", command=self._choose_current_file).grid(row=1, column=2, pady=(0, 8))

        ttk.Label(controls, textvariable=self.previous_data_date_var).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(controls, textvariable=self.current_data_date_var).grid(row=2, column=2, sticky="e")

        ttk.Button(controls, text="Run Analysis", command=self._run_analysis).grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))

        content = ttk.Notebook(self.root)
        content.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))

        summary_tab = ttk.Frame(content, padding=12)
        starts_tab = ttk.Frame(content, padding=12)
        finishes_tab = ttk.Frame(content, padding=12)

        content.add(summary_tab, text="Summary")
        content.add(starts_tab, text="Starts Detail")
        content.add(finishes_tab, text="Finishes Detail")

        self._build_summary_tab(summary_tab)
        self._build_detail_tab(starts_tab, detail_type="start")
        self._build_detail_tab(finishes_tab, detail_type="finish")

        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(16, 8))
        status_bar.grid(row=2, column=0, sticky="ew")

    def _build_summary_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(3, weight=1)
        parent.rowconfigure(5, weight=3)

        ttk.Label(parent, text="Starts Summary").grid(row=0, column=0, sticky="w")
        self.starts_tree = self._create_summary_tree(parent)
        self.starts_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(4, 12))

        ttk.Label(parent, text="Finishes Summary").grid(row=2, column=0, sticky="w")
        self.finishes_tree = self._create_summary_tree(parent)
        self.finishes_tree.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(4, 12))

        ttk.Label(parent, text="Planned vs Actualized").grid(row=4, column=0, sticky="w")
        chart_holder = ttk.Frame(parent)
        chart_holder.grid(row=5, column=0, columnspan=2, sticky="nsew")
        chart_holder.columnconfigure(0, weight=1)
        chart_holder.rowconfigure(0, weight=1)

        self.chart_figure = Figure(figsize=(10, 5), dpi=100)
        self.chart_canvas = FigureCanvasTkAgg(self.chart_figure, master=chart_holder)
        self.chart_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def _build_detail_tab(self, parent: ttk.Frame, *, detail_type: str) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(3, weight=1)

        planned_label = "Actualized Planned Starts" if detail_type == "start" else "Actualized Planned Finishes"
        unplanned_label = "Actualized Unplanned Starts" if detail_type == "start" else "Actualized Unplanned Finishes"

        ttk.Label(parent, text=planned_label).grid(row=0, column=0, sticky="w", pady=(0, 4))
        planned_frame = ttk.Frame(parent)
        planned_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        planned_frame.columnconfigure(0, weight=1)
        planned_frame.rowconfigure(0, weight=1)
        planned_tree = self._create_actualized_detail_tree(planned_frame)
        planned_tree.grid(row=0, column=0, sticky="nsew")
        planned_scrollbar = ttk.Scrollbar(planned_frame, orient="vertical", command=planned_tree.yview)
        planned_tree.configure(yscrollcommand=planned_scrollbar.set)
        planned_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(parent, text=unplanned_label).grid(row=2, column=0, sticky="w", pady=(0, 4))
        unplanned_frame = ttk.Frame(parent)
        unplanned_frame.grid(row=3, column=0, sticky="nsew")
        unplanned_frame.columnconfigure(0, weight=1)
        unplanned_frame.rowconfigure(0, weight=1)
        unplanned_tree = self._create_actualized_detail_tree(unplanned_frame)
        unplanned_tree.grid(row=0, column=0, sticky="nsew")
        unplanned_scrollbar = ttk.Scrollbar(unplanned_frame, orient="vertical", command=unplanned_tree.yview)
        unplanned_tree.configure(yscrollcommand=unplanned_scrollbar.set)
        unplanned_scrollbar.grid(row=0, column=1, sticky="ns")

        if detail_type == "start":
            self.actualized_planned_start_tree = planned_tree
            self.actualized_unplanned_start_tree = unplanned_tree
        else:
            self.actualized_planned_finish_tree = planned_tree
            self.actualized_unplanned_finish_tree = unplanned_tree

    def _create_actualized_detail_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        columns = ("branch", "activity_id", "activity_name", "planned_date", "actual_date", "match_method")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        headings = {
            "branch": "WBS Branch",
            "activity_id": "Activity ID",
            "activity_name": "Activity Name",
            "planned_date": "Planned Date",
            "actual_date": "Actual Date",
            "match_method": "Match Method",
        }
        widths = {
            "branch": 130,
            "activity_id": 130,
            "activity_name": 260,
            "planned_date": 140,
            "actual_date": 140,
            "match_method": 120,
        }
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w")
        return tree

    def _create_summary_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        columns = (
            "branch",
            "planned_count",
            "actualized_planned_count",
            "total_actualized_count",
            "unplanned_actualized_count",
            "planned_completion_percentage",
            "planned_share_of_actualized_percentage",
        )
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=4)
        tree.heading("branch", text="WBS Branch")
        tree.heading("planned_count", text="Planned")
        tree.heading("actualized_planned_count", text="Planned + Actualized")
        tree.heading("total_actualized_count", text="Total Actualized")
        tree.heading("unplanned_actualized_count", text="Unplanned Actualized")
        tree.heading("planned_completion_percentage", text="Planned Completion %")
        tree.heading("planned_share_of_actualized_percentage", text="Planned Share Of Actuals %")
        tree.column("branch", width=150, anchor="w")
        tree.column("planned_count", width=90, anchor="center")
        tree.column("actualized_planned_count", width=135, anchor="center")
        tree.column("total_actualized_count", width=120, anchor="center")
        tree.column("unplanned_actualized_count", width=140, anchor="center")
        tree.column("planned_completion_percentage", width=150, anchor="center")
        tree.column("planned_share_of_actualized_percentage", width=180, anchor="center")
        return tree

    def _choose_previous_file(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("Primavera XER", "*.xer"), ("All Files", "*.*")])
        if selected:
            self.previous_path_var.set(selected)

    def _choose_current_file(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("Primavera XER", "*.xer"), ("All Files", "*.*")])
        if selected:
            self.current_path_var.set(selected)

    def _run_analysis(self) -> None:
        previous_path = Path(self.previous_path_var.get().strip())
        current_path = Path(self.current_path_var.get().strip())

        if not previous_path.is_file() or not current_path.is_file():
            messagebox.showerror("Missing Files", "Select valid previous and current XER files before running the analysis.")
            return

        try:
            previous_schedule = parse_xer_file(previous_path)
            current_schedule = parse_xer_file(current_path)
            result = analyze_schedules(previous_schedule, current_schedule)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Analysis Error", str(exc))
            return

        self.previous_data_date_var.set(
            f"Previous Data Date: {result.previous_data_date.strftime('%Y-%m-%d %H:%M')}"
        )
        self.current_data_date_var.set(
            f"Current Data Date: {result.current_data_date.strftime('%Y-%m-%d %H:%M')}"
        )
        self.status_var.set(self._build_status_message(result))

        self._populate_summary_tree(self.starts_tree, result.starts_summary)
        self._populate_summary_tree(self.finishes_tree, result.finishes_summary)
        self._populate_actualized_detail_tree(
            self.actualized_planned_start_tree, result.actualized_planned_start_details
        )
        self._populate_actualized_detail_tree(
            self.actualized_unplanned_start_tree, result.actualized_unplanned_start_details
        )
        self._populate_actualized_detail_tree(
            self.actualized_planned_finish_tree, result.actualized_planned_finish_details
        )
        self._populate_actualized_detail_tree(
            self.actualized_unplanned_finish_tree, result.actualized_unplanned_finish_details
        )
        self._draw_chart(result)

    def _populate_summary_tree(self, tree: ttk.Treeview | None, rows) -> None:
        if tree is None:
            return
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    row.branch,
                    row.planned_count,
                    row.actualized_planned_count,
                    row.total_actualized_count,
                    row.unplanned_actualized_count,
                    f"{row.planned_completion_percentage:.1f}%",
                    f"{row.planned_share_of_actualized_percentage:.1f}%",
                ),
            )

    def _populate_actualized_detail_tree(
        self,
        tree: ttk.Treeview | None,
        rows: list[ActualizedActivityDetail],
    ) -> None:
        if tree is None:
            return
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    row.branch,
                    row.activity_id,
                    row.activity_name,
                    row.planned_date.strftime("%Y-%m-%d %H:%M") if row.planned_date else "",
                    row.actual_date.strftime("%Y-%m-%d %H:%M"),
                    row.match_method,
                ),
            )

    def _draw_chart(self, result: AnalysisResult) -> None:
        if self.chart_figure is None or self.chart_canvas is None:
            return

        self.chart_figure.clear()

        ax_starts = self.chart_figure.add_subplot(121)
        ax_finishes = self.chart_figure.add_subplot(122)

        branches = [row.branch for row in result.starts_summary]
        x_positions = range(len(branches))
        bar_width = 0.25

        starts_planned = [row.planned_count for row in result.starts_summary]
        starts_actualized_planned = [row.actualized_planned_count for row in result.starts_summary]
        starts_total_actualized = [row.total_actualized_count for row in result.starts_summary]
        finishes_planned = [row.planned_count for row in result.finishes_summary]
        finishes_actualized_planned = [row.actualized_planned_count for row in result.finishes_summary]
        finishes_total_actualized = [row.total_actualized_count for row in result.finishes_summary]

        left_positions = [position - bar_width for position in x_positions]
        middle_positions = list(x_positions)
        right_positions = [position + bar_width for position in x_positions]

        ax_starts.bar(left_positions, starts_planned, width=bar_width, label="Planned", color="#8fb8de")
        ax_starts.bar(
            middle_positions,
            starts_actualized_planned,
            width=bar_width,
            label="Planned + Actualized",
            color="#2f6f9f",
        )
        ax_starts.bar(
            right_positions,
            starts_total_actualized,
            width=bar_width,
            label="Total Actualized",
            color="#d98f5d",
        )
        ax_starts.set_title("Starts")
        ax_starts.set_xticks(list(x_positions))
        ax_starts.set_xticklabels(branches, rotation=0)
        ax_starts.legend()

        ax_finishes.bar(left_positions, finishes_planned, width=bar_width, label="Planned", color="#b9d7a8")
        ax_finishes.bar(
            middle_positions,
            finishes_actualized_planned,
            width=bar_width,
            label="Planned + Actualized",
            color="#4f8a10",
        )
        ax_finishes.bar(
            right_positions,
            finishes_total_actualized,
            width=bar_width,
            label="Total Actualized",
            color="#c97c4c",
        )
        ax_finishes.set_title("Finishes")
        ax_finishes.set_xticks(list(x_positions))
        ax_finishes.set_xticklabels(branches, rotation=0)
        ax_finishes.legend()

        self.chart_figure.tight_layout()
        self.chart_canvas.draw()

    def _build_status_message(self, result: AnalysisResult) -> str:
        if result.missing_branches:
            missing = ", ".join(result.missing_branches)
            return f"Analysis completed. Missing or empty WBS branch in one of the files: {missing}."
        return "Analysis completed successfully."

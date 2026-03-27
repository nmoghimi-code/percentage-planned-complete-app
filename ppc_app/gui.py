from __future__ import annotations

import csv
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .analyzer import (
    ActivityCheck,
    ActualizedActivityDetail,
    MultiProjectAnalysisResult,
    ProjectAnalysis,
    analyze_schedule_collections,
)
from .xer_parser import parse_xer_projects


class PPCAnalyzerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Percentage Planned Complete")
        self.root.geometry("1240x900")
        self.root.minsize(1080, 760)

        self.previous_path_var = tk.StringVar()
        self.current_path_var = tk.StringVar()
        self.previous_data_date_var = tk.StringVar(value="Previous Data Date(s): -")
        self.current_data_date_var = tk.StringVar(value="Current Data Date(s): -")
        self.status_var = tk.StringVar(value="Select the previous and current XER files, then run the analysis.")

        self.summary_canvas: tk.Canvas | None = None
        self.summary_content: ttk.Frame | None = None
        self.summary_window_id: int | None = None
        self.summary_chart_canvases: list[FigureCanvasTkAgg] = []
        self.current_analysis: MultiProjectAnalysisResult | None = None

        self.planned_start_tree: ttk.Treeview | None = None
        self.actualized_planned_start_tree: ttk.Treeview | None = None
        self.actualized_unplanned_start_tree: ttk.Treeview | None = None
        self.planned_finish_tree: ttk.Treeview | None = None
        self.actualized_planned_finish_tree: ttk.Treeview | None = None
        self.actualized_unplanned_finish_tree: ttk.Treeview | None = None

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

        ttk.Button(controls, text="Run Analysis", command=self._run_analysis).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0)
        )
        ttk.Button(controls, text="Export Detail CSV", command=self._export_detail_csv).grid(
            row=3, column=2, sticky="ew", pady=(12, 0)
        )

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
        parent.rowconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas)

        content.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(self.summary_window_id, width=event.width)
            if self.summary_window_id is not None
            else None,
        )

        self.summary_window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.summary_canvas = canvas
        self.summary_content = content

    def _build_detail_tab(self, parent: ttk.Frame, *, detail_type: str) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(3, weight=1)
        parent.rowconfigure(5, weight=1)

        planned_window_label = (
            "Planned Starts From Previous Update"
            if detail_type == "start"
            else "Planned Finishes From Previous Update"
        )
        planned_label = "Actualized Planned Starts" if detail_type == "start" else "Actualized Planned Finishes"
        unplanned_label = "Actualized Unplanned Starts" if detail_type == "start" else "Actualized Unplanned Finishes"

        ttk.Label(parent, text=planned_window_label).grid(row=0, column=0, sticky="w", pady=(0, 4))
        planned_window_frame = ttk.Frame(parent)
        planned_window_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        planned_window_frame.columnconfigure(0, weight=1)
        planned_window_frame.rowconfigure(0, weight=1)
        planned_window_tree = self._create_planned_detail_tree(planned_window_frame)
        planned_window_tree.grid(row=0, column=0, sticky="nsew")
        planned_window_scrollbar = ttk.Scrollbar(
            planned_window_frame,
            orient="vertical",
            command=planned_window_tree.yview,
        )
        planned_window_tree.configure(yscrollcommand=planned_window_scrollbar.set)
        planned_window_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(parent, text=planned_label).grid(row=2, column=0, sticky="w", pady=(0, 4))
        planned_frame = ttk.Frame(parent)
        planned_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        planned_frame.columnconfigure(0, weight=1)
        planned_frame.rowconfigure(0, weight=1)
        planned_tree = self._create_actualized_detail_tree(planned_frame)
        planned_tree.grid(row=0, column=0, sticky="nsew")
        planned_scrollbar = ttk.Scrollbar(planned_frame, orient="vertical", command=planned_tree.yview)
        planned_tree.configure(yscrollcommand=planned_scrollbar.set)
        planned_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(parent, text=unplanned_label).grid(row=4, column=0, sticky="w", pady=(0, 4))
        unplanned_frame = ttk.Frame(parent)
        unplanned_frame.grid(row=5, column=0, sticky="nsew")
        unplanned_frame.columnconfigure(0, weight=1)
        unplanned_frame.rowconfigure(0, weight=1)
        unplanned_tree = self._create_actualized_detail_tree(unplanned_frame)
        unplanned_tree.grid(row=0, column=0, sticky="nsew")
        unplanned_scrollbar = ttk.Scrollbar(unplanned_frame, orient="vertical", command=unplanned_tree.yview)
        unplanned_tree.configure(yscrollcommand=unplanned_scrollbar.set)
        unplanned_scrollbar.grid(row=0, column=1, sticky="ns")

        if detail_type == "start":
            self.planned_start_tree = planned_window_tree
            self.actualized_planned_start_tree = planned_tree
            self.actualized_unplanned_start_tree = unplanned_tree
        else:
            self.planned_finish_tree = planned_window_tree
            self.actualized_planned_finish_tree = planned_tree
            self.actualized_unplanned_finish_tree = unplanned_tree

    def _create_planned_detail_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        columns = ("branch", "activity_id", "activity_name", "planned_date", "actual_date", "status", "match_method")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        headings = {
            "branch": "WBS Branch",
            "activity_id": "Activity ID",
            "activity_name": "Activity Name",
            "planned_date": "Planned Date",
            "actual_date": "Actual Date",
            "status": "Actualized In Window",
            "match_method": "Match Method",
        }
        widths = {
            "branch": 140,
            "activity_id": 130,
            "activity_name": 240,
            "planned_date": 140,
            "actual_date": 140,
            "status": 120,
            "match_method": 120,
        }
        return self._configure_tree(tree, headings, widths)

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
            "branch": 140,
            "activity_id": 130,
            "activity_name": 240,
            "planned_date": 140,
            "actual_date": 140,
            "match_method": 120,
        }
        return self._configure_tree(tree, headings, widths)

    def _configure_tree(
        self,
        tree: ttk.Treeview,
        headings: dict[str, str],
        widths: dict[str, int],
    ) -> ttk.Treeview:
        for column, heading in headings.items():
            tree.heading(column, text=heading)
            tree.column(column, width=widths[column], anchor="w")
        bold_font = tkfont.nametofont("TkDefaultFont").copy()
        bold_font.configure(weight="bold")
        tree.tag_configure("project_header", background="#eef3f7", font=bold_font)
        return tree

    def _create_summary_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        columns = (
            "branch",
            "planned_count",
            "actualized_planned_count",
            "total_actualized_count",
            "unplanned_actualized_count",
            "planned_completion_percentage",
            "total_actualized_over_planned_percentage",
            "planned_share_of_actualized_percentage",
        )
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=4)
        tree.heading("branch", text="WBS Branch")
        tree.heading("planned_count", text="Planned")
        tree.heading("actualized_planned_count", text="Planned + Actualized")
        tree.heading("total_actualized_count", text="Total Actualized")
        tree.heading("unplanned_actualized_count", text="Unplanned Actualized")
        tree.heading("planned_completion_percentage", text="Planned Completion %")
        tree.heading("total_actualized_over_planned_percentage", text="Total Actuals / Planned %")
        tree.heading("planned_share_of_actualized_percentage", text="Planned Share Of Actuals %")
        tree.column("branch", width=180, anchor="w")
        tree.column("planned_count", width=90, anchor="center")
        tree.column("actualized_planned_count", width=135, anchor="center")
        tree.column("total_actualized_count", width=120, anchor="center")
        tree.column("unplanned_actualized_count", width=140, anchor="center")
        tree.column("planned_completion_percentage", width=150, anchor="center")
        tree.column("total_actualized_over_planned_percentage", width=165, anchor="center")
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
            previous_schedules = parse_xer_projects(previous_path)
            current_schedules = parse_xer_projects(current_path)
            analysis = analyze_schedule_collections(previous_schedules, current_schedules)
        except Exception as exc:  # noqa: BLE001
            self.current_analysis = None
            messagebox.showerror("Analysis Error", str(exc))
            return

        if not analysis.project_results:
            self.current_analysis = None
            messagebox.showerror("Analysis Error", "No matching projects were found between the two XER files.")
            return

        self.current_analysis = analysis
        self.previous_data_date_var.set(f"Previous Data Date(s): {self._format_file_dates(previous_schedules)}")
        self.current_data_date_var.set(f"Current Data Date(s): {self._format_file_dates(current_schedules)}")
        self.status_var.set(self._build_status_message(analysis))

        self._populate_summary_projects(analysis)
        self._populate_planned_detail_tree(
            self.planned_start_tree,
            [row for project in analysis.project_results for row in project.result.start_details],
        )
        self._populate_planned_detail_tree(
            self.planned_finish_tree,
            [row for project in analysis.project_results for row in project.result.finish_details],
        )
        self._populate_actualized_detail_tree(
            self.actualized_planned_start_tree,
            [row for project in analysis.project_results for row in project.result.actualized_planned_start_details],
        )
        self._populate_actualized_detail_tree(
            self.actualized_unplanned_start_tree,
            [row for project in analysis.project_results for row in project.result.actualized_unplanned_start_details],
        )
        self._populate_actualized_detail_tree(
            self.actualized_planned_finish_tree,
            [row for project in analysis.project_results for row in project.result.actualized_planned_finish_details],
        )
        self._populate_actualized_detail_tree(
            self.actualized_unplanned_finish_tree,
            [row for project in analysis.project_results for row in project.result.actualized_unplanned_finish_details],
        )

    def _export_detail_csv(self) -> None:
        if self.current_analysis is None:
            messagebox.showerror("Export Error", "Run the analysis before exporting the detail CSV.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile="ppc-detail-export.csv",
        )
        if not save_path:
            return

        try:
            with Path(save_path).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    (
                        "tab",
                        "section",
                        "project",
                        "wbs_branch",
                        "activity_id",
                        "activity_name",
                        "planned_date",
                        "actual_date",
                        "actualized_in_window",
                        "match_method",
                    )
                )
                for row in self._detail_export_rows(self.current_analysis):
                    writer.writerow(row)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export Error", str(exc))
            return

        self.status_var.set(f"Detail CSV exported to {Path(save_path).name}.")

    def _detail_export_rows(self, analysis: MultiProjectAnalysisResult) -> list[tuple[str, ...]]:
        rows: list[tuple[str, ...]] = []
        for project in analysis.project_results:
            rows.extend(
                self._planned_export_rows(
                    project.display_name,
                    "Starts Detail",
                    "Planned Starts From Previous Update",
                    project.result.start_details,
                )
            )
            rows.extend(
                self._actualized_export_rows(
                    project.display_name,
                    "Starts Detail",
                    "Actualized Planned Starts",
                    project.result.actualized_planned_start_details,
                )
            )
            rows.extend(
                self._actualized_export_rows(
                    project.display_name,
                    "Starts Detail",
                    "Actualized Unplanned Starts",
                    project.result.actualized_unplanned_start_details,
                )
            )
            rows.extend(
                self._planned_export_rows(
                    project.display_name,
                    "Finishes Detail",
                    "Planned Finishes From Previous Update",
                    project.result.finish_details,
                )
            )
            rows.extend(
                self._actualized_export_rows(
                    project.display_name,
                    "Finishes Detail",
                    "Actualized Planned Finishes",
                    project.result.actualized_planned_finish_details,
                )
            )
            rows.extend(
                self._actualized_export_rows(
                    project.display_name,
                    "Finishes Detail",
                    "Actualized Unplanned Finishes",
                    project.result.actualized_unplanned_finish_details,
                )
            )
        return rows

    def _planned_export_rows(
        self,
        project_name: str,
        tab_name: str,
        section_name: str,
        details: list[ActivityCheck],
    ) -> list[tuple[str, ...]]:
        return [
            (
                tab_name,
                section_name,
                project_name,
                detail.branch,
                detail.activity_id,
                detail.activity_name,
                detail.planned_date.strftime("%Y-%m-%d %H:%M"),
                detail.actual_date.strftime("%Y-%m-%d %H:%M") if detail.actual_date else "",
                "Yes" if detail.actualized else "No",
                detail.match_method,
            )
            for detail in details
        ]

    def _actualized_export_rows(
        self,
        project_name: str,
        tab_name: str,
        section_name: str,
        details: list[ActualizedActivityDetail],
    ) -> list[tuple[str, ...]]:
        return [
            (
                tab_name,
                section_name,
                project_name,
                detail.branch,
                detail.activity_id,
                detail.activity_name,
                detail.planned_date.strftime("%Y-%m-%d %H:%M") if detail.planned_date else "",
                detail.actual_date.strftime("%Y-%m-%d %H:%M"),
                "",
                detail.match_method,
            )
            for detail in details
        ]

    def _populate_summary_projects(self, analysis: MultiProjectAnalysisResult) -> None:
        if self.summary_content is None:
            return

        for child in self.summary_content.winfo_children():
            child.destroy()
        self.summary_chart_canvases.clear()

        self.summary_content.columnconfigure(0, weight=1)

        for index, project in enumerate(analysis.project_results):
            section = ttk.LabelFrame(self.summary_content, text=f"Project: {project.display_name}", padding=12)
            section.grid(row=index, column=0, sticky="ew", pady=(0, 16))
            section.columnconfigure(0, weight=1)
            section.columnconfigure(1, weight=1)

            result = project.result
            ttk.Label(
                section,
                text=(
                    f"Previous Data Date: {result.previous_data_date.strftime('%Y-%m-%d %H:%M')}    "
                    f"Current Data Date: {result.current_data_date.strftime('%Y-%m-%d %H:%M')}"
                ),
            ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

            ttk.Label(section, text="Starts Summary").grid(row=1, column=0, sticky="w")
            starts_tree = self._create_summary_tree(section)
            starts_tree.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 12))
            self._populate_summary_tree(starts_tree, result.starts_summary)

            ttk.Label(section, text="Finishes Summary").grid(row=3, column=0, sticky="w")
            finishes_tree = self._create_summary_tree(section)
            finishes_tree.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 12))
            self._populate_summary_tree(finishes_tree, result.finishes_summary)

            ttk.Label(section, text="Planned vs Actualized").grid(row=5, column=0, sticky="w")
            chart_holder = ttk.Frame(section)
            chart_holder.grid(row=6, column=0, columnspan=2, sticky="ew")
            chart_holder.columnconfigure(0, weight=1)
            figure = Figure(figsize=(9.5, 3.6), dpi=100)
            canvas = FigureCanvasTkAgg(figure, master=chart_holder)
            canvas.get_tk_widget().grid(row=0, column=0, sticky="ew")
            self._draw_chart(figure, result)
            self.summary_chart_canvases.append(canvas)

    def _populate_summary_tree(self, tree: ttk.Treeview, rows) -> None:
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
                    f"{row.total_actualized_over_planned_percentage:.1f}%",
                    f"{row.planned_share_of_actualized_percentage:.1f}%",
                ),
            )

    def _populate_planned_detail_tree(
        self,
        tree: ttk.Treeview | None,
        rows: list[ActivityCheck],
    ) -> None:
        if tree is None:
            return
        tree.delete(*tree.get_children())
        for row in self._with_project_headers(rows):
            if isinstance(row, str):
                tree.insert("", "end", values=(row, "", "", "", "", "", ""), tags=("project_header",))
                continue
            tree.insert(
                "",
                "end",
                values=(
                    row.branch,
                    row.activity_id,
                    row.activity_name,
                    row.planned_date.strftime("%Y-%m-%d %H:%M"),
                    row.actual_date.strftime("%Y-%m-%d %H:%M") if row.actual_date else "",
                    "Yes" if row.actualized else "No",
                    row.match_method,
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
        for row in self._with_project_headers(rows):
            if isinstance(row, str):
                tree.insert("", "end", values=(row, "", "", "", "", ""), tags=("project_header",))
                continue
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

    def _with_project_headers(self, rows: list[ActivityCheck] | list[ActualizedActivityDetail]) -> list[str | ActivityCheck | ActualizedActivityDetail]:
        grouped_rows: list[str | ActivityCheck | ActualizedActivityDetail] = []
        current_project = None
        for row in rows:
            if row.project_name != current_project:
                current_project = row.project_name
                grouped_rows.append(f"Project: {current_project}")
            grouped_rows.append(row)
        return grouped_rows

    def _draw_chart(self, figure: Figure, result) -> None:
        figure.clear()

        ax_starts = figure.add_subplot(121)
        ax_finishes = figure.add_subplot(122)

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
        ax_starts.bar(middle_positions, starts_actualized_planned, width=bar_width, label="Planned + Actualized", color="#2f6f9f")
        ax_starts.bar(right_positions, starts_total_actualized, width=bar_width, label="Total Actualized", color="#d98f5d")
        ax_starts.set_title("Starts")
        ax_starts.set_xticks(list(x_positions))
        ax_starts.set_xticklabels(branches)
        ax_starts.legend()

        ax_finishes.bar(left_positions, finishes_planned, width=bar_width, label="Planned", color="#b9d7a8")
        ax_finishes.bar(middle_positions, finishes_actualized_planned, width=bar_width, label="Planned + Actualized", color="#4f8a10")
        ax_finishes.bar(right_positions, finishes_total_actualized, width=bar_width, label="Total Actualized", color="#c97c4c")
        ax_finishes.set_title("Finishes")
        ax_finishes.set_xticks(list(x_positions))
        ax_finishes.set_xticklabels(branches)
        ax_finishes.legend()

        figure.tight_layout()

    def _format_file_dates(self, schedules) -> str:
        unique_dates = sorted({schedule.project.data_date.strftime("%Y-%m-%d %H:%M") for schedule in schedules})
        return ", ".join(unique_dates)

    def _build_status_message(self, analysis: MultiProjectAnalysisResult) -> str:
        parts = [f"Analysis completed for {len(analysis.project_results)} matched project(s)."]
        if analysis.unmatched_previous_projects:
            parts.append(f"Unmatched previous projects: {', '.join(analysis.unmatched_previous_projects)}.")
        if analysis.unmatched_current_projects:
            parts.append(f"Unmatched current projects: {', '.join(analysis.unmatched_current_projects)}.")
        missing = sorted(
            {
                f"{project.display_name}: {', '.join(project.result.missing_branches)}"
                for project in analysis.project_results
                if project.result.missing_branches
            }
        )
        if missing:
            parts.append(f"Missing or empty branches: {' | '.join(missing)}.")
        return " ".join(parts)

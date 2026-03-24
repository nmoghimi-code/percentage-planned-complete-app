from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ppc_app.analyzer import analyze_schedules
from ppc_app.xer_parser import parse_xer_file


class AnalysisTests(unittest.TestCase):
    def test_analysis_matches_by_activity_id_and_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            previous_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-01-31 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t\tPRECON\tPre-Construction",
                        "%R\t11\t1\t\tCON\tConstruction",
                        "%R\t12\t1\t10\tPRE-01\tPreconstruction Area",
                        "%R\t13\t1\t11\tCON-01\tConstruction Area",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t12\tA100\tEarly Permit\tTask Dependent\t2024-02-02 08:00\t2024-02-07 17:00\t\t",
                        "%R\t101\t1\t12\tA101\tLong Lead Review\tTask Dependent\t2024-02-03 08:00\t2024-02-08 17:00\t\t",
                        "%R\t200\t1\t13\tB200\tSite Prep\tTask Dependent\t2024-02-04 08:00\t2024-02-09 17:00\t\t",
                        "%R\t201\t1\t13\tB201\tConcrete\tTask Dependent\t2024-02-05 08:00\t2024-02-10 17:00\t\t",
                        "%R\t202\t1\t13\tB202\tLate Procurement\tTask Dependent\t2024-03-05 08:00\t2024-03-12 17:00\t\t",
                        "%R\t203\t1\t13\tB203\tOwner Approval Milestone\tFinish Milestone\t2024-02-06 08:00\t2024-02-06 08:00\t\t",
                    ]
                ),
                encoding="utf-8",
            )

            current_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-02-15 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t\tPRECON\tPre-Construction",
                        "%R\t11\t1\t\tCON\tConstruction",
                        "%R\t12\t1\t10\tPRE-01\tPreconstruction Area",
                        "%R\t13\t1\t11\tCON-01\tConstruction Area",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t12\tA100\tEarly Permit\tTask Dependent\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00",
                        "%R\t101\t1\t12\t\tLong Lead Review\tTask Dependent\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t",
                        "%R\t200\t1\t13\tB200\tSite Prep\tTask Dependent\t2024-02-04 08:00\t2024-02-09 17:00\t2024-02-04 08:00\t2024-02-09 17:00",
                        "%R\t201\t1\t13\tB201\tConcrete\tTask Dependent\t2024-02-05 08:00\t2024-02-10 17:00\t\t",
                        "%R\t202\t1\t13\tB202\tLate Procurement\tTask Dependent\t2024-03-05 08:00\t2024-03-12 17:00\t2024-02-06 08:00\t2024-02-11 17:00",
                        "%R\t203\t1\t13\tB203\tOwner Approval Milestone\tFinish Milestone\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00",
                    ]
                ),
                encoding="utf-8",
            )

            previous_schedule = parse_xer_file(previous_file)
            current_schedule = parse_xer_file(current_file)

            result = analyze_schedules(previous_schedule, current_schedule)

            starts = {row.branch: row for row in result.starts_summary}
            finishes = {row.branch: row for row in result.finishes_summary}

            self.assertEqual(starts["Preconstruction"].planned_count, 2)
            self.assertEqual(starts["Preconstruction"].actualized_planned_count, 2)
            self.assertEqual(starts["Preconstruction"].total_actualized_count, 2)
            self.assertEqual(starts["Preconstruction"].unplanned_actualized_count, 0)
            self.assertEqual(finishes["Preconstruction"].planned_count, 2)
            self.assertEqual(finishes["Preconstruction"].actualized_planned_count, 1)
            self.assertEqual(finishes["Preconstruction"].total_actualized_count, 1)
            self.assertEqual(finishes["Preconstruction"].unplanned_actualized_count, 0)

            self.assertEqual(starts["Construction"].planned_count, 2)
            self.assertEqual(starts["Construction"].actualized_planned_count, 1)
            self.assertEqual(starts["Construction"].total_actualized_count, 2)
            self.assertEqual(starts["Construction"].unplanned_actualized_count, 1)
            self.assertEqual(finishes["Construction"].planned_count, 2)
            self.assertEqual(finishes["Construction"].actualized_planned_count, 1)
            self.assertEqual(finishes["Construction"].total_actualized_count, 2)
            self.assertEqual(finishes["Construction"].unplanned_actualized_count, 1)

            self.assertAlmostEqual(starts["Construction"].planned_completion_percentage, 50.0)
            self.assertAlmostEqual(starts["Construction"].planned_share_of_actualized_percentage, 50.0)

            self.assertEqual(len(result.actualized_planned_start_details), 3)
            self.assertEqual(len(result.actualized_unplanned_start_details), 1)
            self.assertEqual(len(result.actualized_planned_finish_details), 2)
            self.assertEqual(len(result.actualized_unplanned_finish_details), 1)

            unplanned_start = result.actualized_unplanned_start_details[0]
            self.assertEqual(unplanned_start.activity_name, "Late Procurement")
            self.assertNotIn(
                "Owner Approval Milestone",
                {detail.activity_name for detail in result.actualized_unplanned_start_details},
            )
            self.assertNotIn(
                "Owner Approval Milestone",
                {detail.activity_name for detail in result.actualized_unplanned_finish_details},
            )

            precon_name_match = next(
                detail for detail in result.start_details if detail.activity_name == "Long Lead Review"
            )
            self.assertEqual(precon_name_match.match_method, "Activity Name")


if __name__ == "__main__":
    unittest.main()

"""E2E 스모크: submission, 테스터 저장, 관리자 승인·검증·에러 코드."""

import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import session_local
from app.main import app
from app.models import TestResult
from app.scripts.seed_sample_data import seed_sample_data


def _unique_row_payload(form_submission_id: str | None) -> dict:
    u = str(uuid.uuid4())[:8]
    return {
        "key_1": f"Co{u}",
        "key_2": f"Us{u}",
        "key_3": f"Md{u}",
        "key_4": f"Pr{u}",
        "form_submission_id": form_submission_id,
        "field_01": "a",
        "field_02": "b",
    }


def _set_logged_in_cookies(client: TestClient, *, role_name: str = "tester") -> None:
    client.cookies.set("phone_number", "01000000000")
    client.cookies.set("role_name", role_name)


class TestMvpE2ESubmission(unittest.TestCase):
    def test_create_save_approve_reviews_rows(self) -> None:
        with TestClient(app) as client:
            r = client.post("/submission/create")
            self.assertEqual(r.status_code, 200, r.text)
            body = r.json()
            self.assertIn("form_submission_id", body)
            self.assertIn("status", body)
            self.assertEqual(body["status"], "draft")
            sid = body["form_submission_id"]
            self.assertTrue(str(sid).startswith("form_"))

            r2 = client.post(
                "/tester/rows/save_all",
                json={"rows": [_unique_row_payload(sid)], "delete_row_ids": []},
            )
            self.assertEqual(r2.status_code, 200, r2.text)

            s1 = client.post(
                "/submission/submit",
                data={"form_submission_id": sid},
            )
            self.assertEqual(s1.status_code, 200, s1.text)
            self.assertEqual(s1.json().get("status"), "submitted")

            r3 = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": sid},
                follow_redirects=False,
            )
            self.assertEqual(r3.status_code, 303, r3.text)
            self.assertIn(r3.headers.get("location", ""), ("/admin", "http://testserver/admin"))

        with session_local() as session:
            tr = session.execute(select(TestResult).where(TestResult.form_submission_id == sid)).scalar_one()
            self.assertTrue(tr.is_reviewed)

    def test_save_all_without_form_submission_id_returns_400(self) -> None:
        with TestClient(app) as client:
            row = _unique_row_payload(None)
            r = client.post(
                "/tester/rows/save_all",
                json={"rows": [row], "delete_row_ids": []},
            )
            self.assertEqual(r.status_code, 400, r.text)

    def test_approve_missing_form_submission_id_returns_400(self) -> None:
        with TestClient(app) as client:
            r = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": ""},
            )
            self.assertEqual(r.status_code, 400, r.text)
            d = r.json()
            self.assertIn("detail", d)

    def test_approve_unknown_submission_id_returns_404(self) -> None:
        with TestClient(app) as client:
            r = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": "form_does_not_exist_20260101_9999"},
            )
            self.assertEqual(r.status_code, 404, r.text)

    def test_approve_submission_with_zero_rows_returns_400(self) -> None:
        with TestClient(app) as client:
            r0 = client.post("/submission/create")
            self.assertEqual(r0.status_code, 200, r0.text)
            sid = r0.json()["form_submission_id"]
            # 제출 완료는 행이 0건이면 400
            s = client.post("/submission/submit", data={"form_submission_id": sid})
            self.assertEqual(s.status_code, 400, s.text)
            r = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": sid},
            )
            self.assertEqual(r.status_code, 400, r.text)

    def test_approve_valid_submission_marks_rows_reviewed_idempotent_303(self) -> None:
        with TestClient(app) as client:
            r0 = client.post("/submission/create")
            sid = r0.json()["form_submission_id"]
            client.post(
                "/tester/rows/save_all",
                json={"rows": [_unique_row_payload(sid)], "delete_row_ids": []},
            )
            # draft 상태 승인 불가
            draft_approve = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": sid},
            )
            self.assertEqual(draft_approve.status_code, 400, draft_approve.text)
            # 제출 완료 후 승인 가능
            s1 = client.post("/submission/submit", data={"form_submission_id": sid})
            self.assertEqual(s1.status_code, 200, s1.text)
            a1 = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": sid},
                follow_redirects=False,
            )
            self.assertEqual(a1.status_code, 303, a1.text)
            a2 = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": sid},
                follow_redirects=False,
            )
            self.assertEqual(a2.status_code, 303, a2.text)
        with session_local() as session:
            tr = session.execute(select(TestResult).where(TestResult.form_submission_id == sid)).scalar_one()
            self.assertTrue(tr.is_reviewed)

    def test_admin_submission_summary_html_before_and_after_approve(self) -> None:
        with TestClient(app) as client:
            _set_logged_in_cookies(client, role_name="admin")
            r0 = client.post("/submission/create")
            self.assertEqual(r0.status_code, 200, r0.text)
            sid = r0.json()["form_submission_id"]
            client.post(
                "/tester/rows/save_all",
                json={"rows": [_unique_row_payload(sid)], "delete_row_ids": []},
            )
            a1 = client.get("/admin")
            self.assertEqual(a1.status_code, 200, a1.text)
            self.assertIn(sid, a1.text)
            self.assertIn("데이터 입력승인", a1.text)
            # headers (Korean raw sample mapping)
            self.assertIn("양식 제출 ID", a1.text)
            self.assertIn("월", a1.text)
            self.assertIn("검사대수", a1.text)
            self.assertIn("저온 투입일", a1.text)
            self.assertIn("저온 완료일", a1.text)
            self.assertIn("저온 시간", a1.text)
            self.assertIn("고온 투입일", a1.text)
            self.assertIn("고온 완료일", a1.text)
            self.assertIn("고온 시간", a1.text)
            self.assertNotIn("col 1", a1.text)
            self.assertNotIn("col_2", a1.text)
            s1 = client.post("/submission/submit", data={"form_submission_id": sid})
            self.assertEqual(s1.status_code, 200, s1.text)
            ap = client.post(
                "/admin/submission/approve",
                data={"form_submission_id": sid},
                follow_redirects=False,
            )
            self.assertEqual(ap.status_code, 303, ap.text)
            a2 = client.get("/admin")
            self.assertEqual(a2.status_code, 200, a2.text)
            self.assertIn(sid, a2.text)
            self.assertIn("데이터 입력승인", a2.text)

    def test_admin_delete_replaces_rejection(self) -> None:
        with TestClient(app) as client:
            r0 = client.post("/submission/create")
            sid = r0.json()["form_submission_id"]
            client.post(
                "/tester/rows/save_all",
                json={"rows": [_unique_row_payload(sid)], "delete_row_ids": []},
            )
            # submitted 상태에서 delete 허용
            client.post("/submission/submit", data={"form_submission_id": sid})
            d1 = client.post(
                "/admin/submission/delete",
                data={"form_submission_id": sid},
                follow_redirects=False,
            )
            self.assertEqual(d1.status_code, 303, d1.text)
            # 삭제 후 승인하면 404
            a1 = client.post("/admin/submission/approve", data={"form_submission_id": sid})
            self.assertEqual(a1.status_code, 404, a1.text)

    def test_admin_delete_forbidden_when_approved(self) -> None:
        with TestClient(app) as client:
            r0 = client.post("/submission/create")
            sid = r0.json()["form_submission_id"]
            client.post(
                "/tester/rows/save_all",
                json={"rows": [_unique_row_payload(sid)], "delete_row_ids": []},
            )
            client.post("/submission/submit", data={"form_submission_id": sid})
            client.post("/admin/submission/approve", data={"form_submission_id": sid}, follow_redirects=False)
            d1 = client.post("/admin/submission/delete", data={"form_submission_id": sid})
            self.assertEqual(d1.status_code, 400, d1.text)

    def test_page_title_texts_appear(self) -> None:
        with TestClient(app) as client:
            _set_logged_in_cookies(client, role_name="tester")
            t = client.get("/tester")
            self.assertEqual(t.status_code, 200, t.text)
            self.assertIn("ELT 시험 데이터 입력 시스템", t.text)
            _set_logged_in_cookies(client, role_name="admin")
            a = client.get("/admin")
            self.assertEqual(a.status_code, 200, a.text)
            self.assertIn("ELT 시험 데이터 트래킹 시스템", a.text)

    def test_seed_sample_data_consistency(self) -> None:
        with session_local() as session:
            seed_sample_data(session)
            sample_ids = [
                "form_sample_draft_001",
                "form_sample_submitted_001",
                "form_sample_approved_001",
            ]
            for sid in sample_ids:
                rows = session.execute(
                    select(TestResult).where(TestResult.form_submission_id == sid)
                ).scalars().all()
                self.assertGreaterEqual(len(rows), 3)
                self.assertTrue(all((r.form_submission_id or "").strip() == sid for r in rows))
            approved_rows = session.execute(
                select(TestResult).where(TestResult.form_submission_id == "form_sample_approved_001")
            ).scalars().all()
            self.assertTrue(all(r.is_reviewed for r in approved_rows))
            submitted_rows = session.execute(
                select(TestResult).where(TestResult.form_submission_id == "form_sample_submitted_001")
            ).scalars().all()
            self.assertTrue(all(not r.is_reviewed for r in submitted_rows))

            # 업체명 raw sample coverage across all sample rows
            all_rows = session.execute(
                select(TestResult).where(TestResult.form_submission_id.in_(sample_ids))
            ).scalars().all()
            companies = {str(r.key_1 or "").strip() for r in all_rows if str(r.key_1 or "").strip()}
            for required in {
                "컨포커스",
                "윌템스_검안기",
                "윌템스_덴탈",
                "사이언스테라",
                "JHT",
                "윌템스",
                "컨포커스-호롭터",
            }:
                self.assertIn(required, companies)

    def test_admin_page_contains_raw_sample_values(self) -> None:
        with session_local() as session:
            seed_sample_data(session)
        with TestClient(app) as client:
            _set_logged_in_cookies(client, role_name="admin")
            html = client.get("/admin").text
            # 업체명 raw sample coverage
            for company in [
                "컨포커스",
                "윌템스_검안기",
                "윌템스_덴탈",
                "사이언스테라",
                "JHT",
                "윌템스",
                "컨포커스-호롭터",
            ]:
                self.assertIn(company, html)
            self.assertIn("HBM-1", html)
            self.assertIn("2502-H009", html)


if __name__ == "__main__":
    unittest.main()

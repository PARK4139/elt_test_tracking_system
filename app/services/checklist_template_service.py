from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import ChecklistTemplate, ModelChecklistTemplateMap


CHECKLIST_SLOT_FIELD_NAMES = [
    "key_3",
    "key_4",
    "field_01",
    "field_02",
    "field_03",
    "field_04",
    "field_05",
    "field_06",
    "field_07",
    "field_10",
    "field_11",
    "field_12",
    "field_13",
    "field_14",
    "field_18",
]

DEFAULT_TEMPLATE_NAME = "ELT ROOM CHECK SHEET (Rev_1)"
DEFAULT_MODEL_NAMES = ["HBM-1", "HOCT-1", "HOCT-1F"]


def _normalize_template_name(template_name: str) -> str:
    return str(template_name or "").strip()


def _normalize_model_name(model_name: str) -> str:
    return str(model_name or "").strip()


def _normalize_item_labels(item_labels: list[str]) -> list[str]:
    normalized = [str(item_label or "").strip() for item_label in item_labels]
    padded = normalized[:15]
    while len(padded) < 15:
        padded.append("")
    return padded


def _template_item_label_payload(template_row: ChecklistTemplate) -> list[str]:
    return [
        str(template_row.item_label_01 or "").strip(),
        str(template_row.item_label_02 or "").strip(),
        str(template_row.item_label_03 or "").strip(),
        str(template_row.item_label_04 or "").strip(),
        str(template_row.item_label_05 or "").strip(),
        str(template_row.item_label_06 or "").strip(),
        str(template_row.item_label_07 or "").strip(),
        str(template_row.item_label_08 or "").strip(),
        str(template_row.item_label_09 or "").strip(),
        str(template_row.item_label_10 or "").strip(),
        str(template_row.item_label_11 or "").strip(),
        str(template_row.item_label_12 or "").strip(),
        str(template_row.item_label_13 or "").strip(),
        str(template_row.item_label_14 or "").strip(),
        str(template_row.item_label_15 or "").strip(),
    ]


def ensure_default_checklist_templates(database_session: Session) -> None:
    changed = False
    template_row = database_session.get(ChecklistTemplate, DEFAULT_TEMPLATE_NAME)
    if template_row is None:
        template_row = ChecklistTemplate(
            template_name=DEFAULT_TEMPLATE_NAME,
            item_label_01="모델명",
            item_label_02="공정번호",
            item_label_03="월",
            item_label_04="검사대수",
            item_label_05="시험 항목 01",
            item_label_06="시험 항목 02",
            item_label_07="시험 항목 03",
            item_label_08="시험 항목 04",
            item_label_09="시험 항목 05",
            item_label_10="시험 항목 06",
            item_label_11="시험 항목 07",
            item_label_12="시험 항목 08",
            item_label_13="시험 항목 09",
            item_label_14="시험 항목 10",
            item_label_15="불합격 제품 SERIAL NO.",
        )
        database_session.add(template_row)
        changed = True

    for model_name in DEFAULT_MODEL_NAMES:
        existing_map = database_session.get(ModelChecklistTemplateMap, model_name)
        if existing_map is not None:
            continue
        database_session.add(
            ModelChecklistTemplateMap(
                model_name=model_name,
                template_name=DEFAULT_TEMPLATE_NAME,
            )
        )
        changed = True

    if changed:
        database_session.commit()


def list_checklist_templates(database_session: Session) -> list[ChecklistTemplate]:
    return list(
        database_session.scalars(
            select(ChecklistTemplate).order_by(ChecklistTemplate.template_name.asc())
        )
    )


def list_model_checklist_template_maps(database_session: Session) -> list[ModelChecklistTemplateMap]:
    return list(
        database_session.scalars(
            select(ModelChecklistTemplateMap).order_by(ModelChecklistTemplateMap.model_name.asc())
        )
    )


def build_template_payload_map(database_session: Session) -> dict[str, dict]:
    payload_map: dict[str, dict] = {}
    for template_row in list_checklist_templates(database_session):
        payload_map[template_row.template_name] = {
            "template_name": template_row.template_name,
            "item_labels": _template_item_label_payload(template_row),
        }
    return payload_map


def build_model_template_payload_map(database_session: Session) -> dict[str, dict]:
    template_payload_map = build_template_payload_map(database_session)
    payload_map: dict[str, dict] = {}
    for row in list_model_checklist_template_maps(database_session):
        template_payload = template_payload_map.get(row.template_name)
        if template_payload is None:
            payload_map[row.model_name] = {
                "template_name": row.template_name,
                "item_labels": [""] * 15,
            }
            continue
        payload_map[row.model_name] = {
            "template_name": template_payload["template_name"],
            "item_labels": list(template_payload["item_labels"]),
        }
    return payload_map


def upsert_checklist_template(
    database_session: Session,
    template_name: str,
    item_labels: list[str],
) -> ChecklistTemplate:
    normalized_template_name = _normalize_template_name(template_name)
    if not normalized_template_name:
        raise ValueError("양식명을 입력해 주세요.")
    normalized_item_labels = _normalize_item_labels(item_labels)
    template_row = database_session.get(ChecklistTemplate, normalized_template_name)
    if template_row is None:
        template_row = ChecklistTemplate(template_name=normalized_template_name)
        database_session.add(template_row)
    (
        template_row.item_label_01,
        template_row.item_label_02,
        template_row.item_label_03,
        template_row.item_label_04,
        template_row.item_label_05,
        template_row.item_label_06,
        template_row.item_label_07,
        template_row.item_label_08,
        template_row.item_label_09,
        template_row.item_label_10,
        template_row.item_label_11,
        template_row.item_label_12,
        template_row.item_label_13,
        template_row.item_label_14,
        template_row.item_label_15,
    ) = normalized_item_labels
    database_session.commit()
    database_session.refresh(template_row)
    return template_row


def delete_checklist_template(database_session: Session, template_name: str) -> bool:
    normalized_template_name = _normalize_template_name(template_name)
    if not normalized_template_name:
        raise ValueError("양식명을 선택해 주세요.")
    database_session.execute(
        delete(ModelChecklistTemplateMap).where(
            ModelChecklistTemplateMap.template_name == normalized_template_name
        )
    )
    result = database_session.execute(
        delete(ChecklistTemplate).where(ChecklistTemplate.template_name == normalized_template_name)
    )
    database_session.commit()
    return bool(result.rowcount)


def upsert_model_checklist_template_map(
    database_session: Session,
    model_name: str,
    template_name: str,
) -> ModelChecklistTemplateMap:
    normalized_model_name = _normalize_model_name(model_name)
    normalized_template_name = _normalize_template_name(template_name)
    if not normalized_model_name:
        raise ValueError("모델명을 입력해 주세요.")
    if not normalized_template_name:
        raise ValueError("양식명을 선택해 주세요.")
    if database_session.get(ChecklistTemplate, normalized_template_name) is None:
        raise ValueError("선택한 양식이 존재하지 않습니다.")
    mapping_row = database_session.get(ModelChecklistTemplateMap, normalized_model_name)
    if mapping_row is None:
        mapping_row = ModelChecklistTemplateMap(
            model_name=normalized_model_name,
            template_name=normalized_template_name,
        )
        database_session.add(mapping_row)
    else:
        mapping_row.template_name = normalized_template_name
    database_session.commit()
    database_session.refresh(mapping_row)
    return mapping_row


def delete_model_checklist_template_map(database_session: Session, model_name: str) -> bool:
    normalized_model_name = _normalize_model_name(model_name)
    if not normalized_model_name:
        raise ValueError("모델명을 선택해 주세요.")
    result = database_session.execute(
        delete(ModelChecklistTemplateMap).where(
            ModelChecklistTemplateMap.model_name == normalized_model_name
        )
    )
    database_session.commit()
    return bool(result.rowcount)

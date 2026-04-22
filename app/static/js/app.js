(() => {
    const tester_grid_body = document.getElementById("tester_grid_body");
    const sample_fill_button = document.getElementById("sample_fill_button");
    const add_row_button = document.getElementById("add_row_button");
    const select_all_rows_button = document.getElementById("select_all_rows_button");
    const delete_selected_rows_button = document.getElementById("delete_selected_rows_button");
    const save_all_rows_button = document.getElementById("save_all_rows_button");
    const save_validation_notice = document.getElementById("save_validation_notice");
    const tester_dropdown_options_json = document.getElementById("tester_dropdown_options_json");
    const pending_deleted_row_ids = new Set();

    if (
        !tester_grid_body ||
        !sample_fill_button ||
        !add_row_button ||
        !select_all_rows_button ||
        !delete_selected_rows_button ||
        !save_all_rows_button ||
        !save_validation_notice ||
        !tester_dropdown_options_json
    ) {
        return;
    }

    let dropdown_options_map = {};
    try {
        dropdown_options_map = JSON.parse(tester_dropdown_options_json.textContent || "{}");
    } catch (_error) {
        dropdown_options_map = {};
    }

    const field_names = [
        "field_01",
        "field_02",
        "field_03",
        "field_04",
        "field_05",
        "field_06",
        "field_07",
        "field_08",
        "field_09",
        "field_10",
    ];
    const required_field_names = ["key_1", "key_2", "key_3", ...field_names];
    const field_label_map = {
        key_1: "업체명",
        key_2: "key_seg 2",
        key_3: "key_seg 3",
        field_01: "temp_col 01",
        field_02: "temp_col 02",
        field_03: "temp_col 03",
        field_04: "temp_col 04",
        field_05: "temp_col 05",
        field_06: "temp_col 06",
        field_07: "temp_col 07",
        field_08: "temp_col 08",
        field_09: "temp_col 09",
        field_10: "temp_col 10",
    };
    const time_field_definitions = [
        { selector: ".low_test_started_at_cell", label: "저온시험 시작" },
        { selector: ".low_test_ended_at_cell", label: "저온시험 종료" },
        { selector: ".high_test_started_at_cell", label: "고온시험 시작" },
        { selector: ".high_test_ended_at_cell", label: "고온시험 종료" },
    ];
    const accepted_time_format_hint = "YYYY-MM-DD (요일) HH:mm:ss";

    const generate_uuid_v7 = () => {
        const bytes = new Uint8Array(16);
        crypto.getRandomValues(bytes);

        const timestamp_ms = BigInt(Date.now());
        bytes[0] = Number((timestamp_ms >> 40n) & 0xffn);
        bytes[1] = Number((timestamp_ms >> 32n) & 0xffn);
        bytes[2] = Number((timestamp_ms >> 24n) & 0xffn);
        bytes[3] = Number((timestamp_ms >> 16n) & 0xffn);
        bytes[4] = Number((timestamp_ms >> 8n) & 0xffn);
        bytes[5] = Number(timestamp_ms & 0xffn);

        bytes[6] = (bytes[6] & 0x0f) | 0x70; // version 7
        bytes[8] = (bytes[8] & 0x3f) | 0x80; // RFC 4122 variant

        const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));
        return (
            `${hex.slice(0, 4).join("")}-` +
            `${hex.slice(4, 6).join("")}-` +
            `${hex.slice(6, 8).join("")}-` +
            `${hex.slice(8, 10).join("")}-` +
            `${hex.slice(10, 16).join("")}`
        );
    };

    const read_error_detail = async (response) => {
        try {
            const payload = await response.json();
            if (payload && payload.detail) {
                return payload.detail;
            }
            return "요청에 실패했습니다.";
        } catch (_error) {
            return "요청에 실패했습니다.";
        }
    };

    const set_action_buttons_disabled = (row_element, disabled) => {
        row_element.querySelector(".low_test_start_button").disabled = disabled;
        row_element.querySelector(".low_test_end_button").disabled = disabled;
        row_element.querySelector(".high_test_start_button").disabled = disabled;
        row_element.querySelector(".high_test_end_button").disabled = disabled;
    };

    const get_completion_flag = (row_element, dataset_key, input_selector) => {
        if (row_element.dataset[dataset_key] === "1") {
            return true;
        }
        if (row_element.dataset[dataset_key] === "0") {
            return false;
        }
        const has_initial_value = !!read_cell_value(row_element.querySelector(input_selector));
        row_element.dataset[dataset_key] = has_initial_value ? "1" : "0";
        return has_initial_value;
    };

    const set_completion_flag = (row_element, dataset_key, completed) => {
        row_element.dataset[dataset_key] = completed ? "1" : "0";
    };

    const update_test_action_buttons = (row_element) => {
        const low_test_started = get_completion_flag(
            row_element,
            "lowTestStartedDone",
            ".low_test_started_at_cell"
        );
        const low_test_ended = get_completion_flag(
            row_element,
            "lowTestEndedDone",
            ".low_test_ended_at_cell"
        );
        const high_test_started = get_completion_flag(
            row_element,
            "highTestStartedDone",
            ".high_test_started_at_cell"
        );
        const high_test_ended = get_completion_flag(
            row_element,
            "highTestEndedDone",
            ".high_test_ended_at_cell"
        );

        const low_test_started_input = row_element.querySelector(".low_test_started_at_cell");
        const low_test_ended_input = row_element.querySelector(".low_test_ended_at_cell");
        const high_test_started_input = row_element.querySelector(".high_test_started_at_cell");
        const high_test_ended_input = row_element.querySelector(".high_test_ended_at_cell");

        const low_test_start_button = row_element.querySelector(".low_test_start_button");
        const low_test_end_button = row_element.querySelector(".low_test_end_button");
        const high_test_start_button = row_element.querySelector(".high_test_start_button");
        const high_test_end_button = row_element.querySelector(".high_test_end_button");

        low_test_started_input.style.display = low_test_started ? "" : "none";
        low_test_ended_input.style.display = low_test_ended ? "" : "none";
        high_test_started_input.style.display = high_test_started ? "" : "none";
        high_test_ended_input.style.display = high_test_ended ? "" : "none";

        low_test_start_button.style.display = low_test_started ? "none" : "";
        low_test_end_button.style.display = low_test_ended ? "none" : "";
        high_test_start_button.style.display = high_test_started ? "none" : "";
        high_test_end_button.style.display = high_test_ended ? "none" : "";

        low_test_start_button.disabled = false;
        low_test_end_button.disabled = !low_test_started || low_test_ended;
        high_test_start_button.disabled = false;
        high_test_end_button.disabled = !high_test_started || high_test_ended;
    };

    const create_row_element = () => {
        const build_select_html = (field_name) => {
            const option_values = Array.isArray(dropdown_options_map[field_name])
                ? dropdown_options_map[field_name]
                : [];
            const option_html = option_values
                .map((option_value) => `<option value="${option_value}">${option_value}</option>`)
                .join("");
            return `<select data-field="${field_name}"><option value=""></option>${option_html}</select>`;
        };

        const row_element = document.createElement("tr");
        row_element.className = "editable_row";
        row_element.dataset.id = "";
        row_element.innerHTML = `
            <td><input class="row_select_checkbox" type="checkbox"></td>
            <td class="id_cell hidden_id_column"></td>
            <td>${build_select_html("key_1")}</td>
            <td>${build_select_html("key_2")}</td>
            <td>${build_select_html("key_3")}</td>
            <td>${build_select_html("field_01")}</td>
            <td>${build_select_html("field_02")}</td>
            <td>${build_select_html("field_03")}</td>
            <td><input data-field="field_04" value=""></td>
            <td><input data-field="field_05" value=""></td>
            <td><input data-field="field_06" value=""></td>
            <td><input data-field="field_07" value=""></td>
            <td><input data-field="field_08" value=""></td>
            <td><input data-field="field_09" value=""></td>
            <td><input data-field="field_10" value=""></td>
            <td class="test_action_td">
                <div class="test_action_cell">
                    <input class="low_test_started_at_cell test_timestamp_input" value="">
                    <button type="button" class="low_test_start_button">저온시험 시작</button>
                </div>
            </td>
            <td class="test_action_td">
                <div class="test_action_cell">
                    <input class="low_test_ended_at_cell test_timestamp_input" value="">
                    <button type="button" class="low_test_end_button">저온시험 종료</button>
                </div>
            </td>
            <td class="low_test_delta_cell"><span class="delta_value is_placeholder">자동계산</span></td>
            <td class="test_action_td">
                <div class="test_action_cell">
                    <input class="high_test_started_at_cell test_timestamp_input" value="">
                    <button type="button" class="high_test_start_button">고온시험 시작</button>
                </div>
            </td>
            <td class="test_action_td">
                <div class="test_action_cell">
                    <input class="high_test_ended_at_cell test_timestamp_input" value="">
                    <button type="button" class="high_test_end_button">고온시험 종료</button>
                </div>
            </td>
            <td class="high_test_delta_cell"><span class="delta_value is_placeholder">자동계산</span></td>
        `;
        return row_element;
    };

    const read_trimmed_value = (row_element, field_name) => {
        const input = row_element.querySelector(`[data-field="${field_name}"]`);
        return input.value.trim();
    };

    const apply_compact_width_to_input = (input_element) => {
        const text_length = Math.max((input_element.value || "").length, 4);
        const width_px = Math.min(80, Math.max(40, text_length * 7 + 8));
        input_element.style.width = `${width_px}px`;
    };

    const bind_compact_width_behavior = (row_element) => {
        const input_elements = row_element.querySelectorAll("input[data-field]");
        for (const input_element of input_elements) {
            apply_compact_width_to_input(input_element);
            input_element.addEventListener("input", () => {
                apply_compact_width_to_input(input_element);
            });
        }
    };

    const build_upsert_payload = (row_element) => {
        const payload = {
            key_1: read_trimmed_value(row_element, "key_1"),
            key_2: read_trimmed_value(row_element, "key_2"),
            key_3: read_trimmed_value(row_element, "key_3"),
        };

        for (const field_name of field_names) {
            const input = row_element.querySelector(`[data-field="${field_name}"]`);
            payload[field_name] = input.value;
        }

        const low_test_started_at_text = read_cell_value(
            row_element.querySelector(".low_test_started_at_cell")
        );
        const low_test_ended_at_text = read_cell_value(
            row_element.querySelector(".low_test_ended_at_cell")
        );
        const high_test_started_at_text = read_cell_value(
            row_element.querySelector(".high_test_started_at_cell")
        );
        const high_test_ended_at_text = read_cell_value(
            row_element.querySelector(".high_test_ended_at_cell")
        );

        payload.low_test_started_at = low_test_started_at_text
            ? parse_datetime_text(low_test_started_at_text)?.toISOString() || null
            : null;
        payload.low_test_ended_at = low_test_ended_at_text
            ? parse_datetime_text(low_test_ended_at_text)?.toISOString() || null
            : null;
        payload.high_test_started_at = high_test_started_at_text
            ? parse_datetime_text(high_test_started_at_text)?.toISOString() || null
            : null;
        payload.high_test_ended_at = high_test_ended_at_text
            ? parse_datetime_text(high_test_ended_at_text)?.toISOString() || null
            : null;

        const low_test_delta_text = (
            row_element.querySelector(".low_test_delta_cell .delta_value")?.textContent || ""
        ).trim();
        const high_test_delta_text = (
            row_element.querySelector(".high_test_delta_cell .delta_value")?.textContent || ""
        ).trim();
        payload.low_test_delta = low_test_delta_text === "자동계산" ? null : low_test_delta_text;
        payload.high_test_delta = high_test_delta_text === "자동계산" ? null : high_test_delta_text;

        return payload;
    };

    const trim_timestamp_input = (input_element) => {
        const trimmed_value = (input_element.value || "").trim();
        input_element.value = trimmed_value;
        return trimmed_value;
    };

    const is_timestamp_format_valid = (value) => {
        if (!value) {
            return true;
        }
        const format_regex =
            /^\d{4}-\d{2}-\d{2}\s(?:\([일월화수목금토]\)\s)?\d{2}:\d{2}:\d{2}$/;
        if (!format_regex.test(value)) {
            return false;
        }
        return parse_datetime_text(value) !== null;
    };

    const parse_datetime_text = (value) => {
        if (!value) {
            return null;
        }
        const without_weekday = value.replace(/\s\([일월화수목금토]\)\s/, " ");
        const normalized_value = without_weekday.includes("T")
            ? without_weekday
            : without_weekday.replace(" ", "T");
        const parsed = new Date(normalized_value);
        if (Number.isNaN(parsed.getTime())) {
            return null;
        }
        return parsed;
    };

    const format_two_digits = (value) => String(value).padStart(2, "0");
    const weekday_names = ["일", "월", "화", "수", "목", "금", "토"];

    const get_now_timestamp_info = () => {
        const now = new Date();
        const year = now.getFullYear();
        const month = format_two_digits(now.getMonth() + 1);
        const day = format_two_digits(now.getDate());
        const hours = format_two_digits(now.getHours());
        const minutes = format_two_digits(now.getMinutes());
        const seconds = format_two_digits(now.getSeconds());
        const weekday = weekday_names[now.getDay()];
        return {
            iso: now.toISOString(),
            display: `${year}-${month}-${day} (${weekday}) ${hours}:${minutes}:${seconds}`,
        };
    };

    const set_timestamp_cell = (cell_element, timestamp_info) => {
        if ("value" in cell_element) {
            cell_element.value = timestamp_info.display;
        } else {
            cell_element.textContent = timestamp_info.display;
        }
        cell_element.dataset.iso = timestamp_info.iso;
    };

    const read_cell_value = (cell_element) => {
        if ("value" in cell_element) {
            return cell_element.value.trim();
        }
        return cell_element.textContent.trim();
    };

    const parse_datetime_from_cell = (cell_element) => {
        const raw_value = read_cell_value(cell_element);
        const parsed_from_raw = parse_datetime_text(raw_value);
        if (parsed_from_raw) {
            return parsed_from_raw;
        }
        const iso_value = cell_element.dataset.iso || "";
        if (iso_value) {
            return parse_datetime_text(iso_value);
        }
        return null;
    };

    const format_duration = (milliseconds) => {
        const total_seconds = Math.floor(milliseconds / 1000);
        const hours = String(Math.floor(total_seconds / 3600)).padStart(2, "0");
        const minutes = String(Math.floor((total_seconds % 3600) / 60)).padStart(2, "0");
        const seconds = String(total_seconds % 60).padStart(2, "0");
        return `${hours}:${minutes}:${seconds}`;
    };

    const render_delta_from_timestamps = (row_element, test_type) => {
        const started_cell = row_element.querySelector(`.${test_type}_started_at_cell`);
        const ended_cell = row_element.querySelector(`.${test_type}_ended_at_cell`);
        const delta_cell = row_element.querySelector(`.${test_type}_delta_cell`);
        const delta_value = delta_cell.querySelector(".delta_value") || delta_cell;
        const started_at = parse_datetime_from_cell(started_cell);
        const ended_at = parse_datetime_from_cell(ended_cell);

        if (!started_at || !ended_at || ended_at < started_at) {
            delta_value.textContent = "자동계산";
            delta_value.classList.add("is_placeholder");
            return;
        }
        delta_value.textContent = format_duration(ended_at.getTime() - started_at.getTime());
        delta_value.classList.remove("is_placeholder");
    };

    const upsert_row = async (row_element, row_index_for_message, submission_id_for_save = null) => {
        const payload = build_upsert_payload(row_element);
        if (submission_id_for_save) {
            payload.submission_id = submission_id_for_save;
        }
        const has_any_value =
            !!payload.key_1 ||
            !!payload.key_2 ||
            !!payload.key_3 ||
            field_names.some((field_name) => String(payload[field_name] || "").trim() !== "") ||
            !!payload.low_test_started_at ||
            !!payload.low_test_ended_at ||
            !!payload.high_test_started_at ||
            !!payload.high_test_ended_at ||
            !!payload.low_test_delta ||
            !!payload.high_test_delta;
        if (!has_any_value) {
            return true;
        }
        if (!payload.key_1 || !payload.key_2 || !payload.key_3) {
            alert(`${row_index_for_message}번째 행: key_1, key_2, key_3는 필수입니다.`);
            return false;
        }

        try {
            const response = await fetch("/tester/rows/upsert", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                alert(await read_error_detail(response));
                return false;
            }

            const upsert_result = await response.json();
            row_element.dataset.id = String(upsert_result.id);
            row_element.querySelector(".id_cell").textContent = String(upsert_result.id);
            row_element.querySelector('[data-field="key_1"]').value = upsert_result.key_1;
            row_element.querySelector('[data-field="key_2"]').value = upsert_result.key_2;
            row_element.querySelector('[data-field="key_3"]').value = upsert_result.key_3;
            apply_compact_width_to_input(row_element.querySelector('[data-field="key_1"]'));
            apply_compact_width_to_input(row_element.querySelector('[data-field="key_2"]'));
            apply_compact_width_to_input(row_element.querySelector('[data-field="key_3"]'));
            update_test_action_buttons(row_element);
            return true;
        } catch (_error) {
            alert("네트워크 오류가 발생했습니다.");
            return false;
        }
    };

    const list_editable_rows = () => Array.from(tester_grid_body.querySelectorAll("tr.editable_row"));
    const list_selected_rows = () =>
        list_editable_rows().filter((row_element) => {
            const checkbox = row_element.querySelector(".row_select_checkbox");
            return checkbox && checkbox.checked;
        });

    const render_non_modal_notice = (message_lines, notice_type) => {
        save_validation_notice.className = `non_modal_notice ${notice_type}`;
        save_validation_notice.innerHTML = message_lines.map((line) => `<div>${line}</div>`).join("");
    };

    const clear_non_modal_notice = () => {
        save_validation_notice.className = "non_modal_notice";
        save_validation_notice.innerHTML = "";
    };

    const get_missing_column_descriptions = (row_element) =>
        required_field_names
            .map((field_name, index) => {
                const input_element = row_element.querySelector(`[data-field="${field_name}"]`);
                const value = input_element ? input_element.value.trim() : "";
                if (value) {
                    return null;
                }
                return `${index + 1}번(${field_label_map[field_name]})`;
            })
            .filter(Boolean);

    sample_fill_button.addEventListener("click", () => {
        clear_non_modal_notice();
        const editable_rows = list_editable_rows();
        if (editable_rows.length === 0) {
            alert("샘플 작성할 행이 없습니다.");
            return;
        }

        for (const row_element of editable_rows) {
            for (const field_name of required_field_names) {
                const field_element = row_element.querySelector(`[data-field="${field_name}"]`);
                if (!field_element) {
                    continue;
                }
                if (!field_element.value.trim()) {
                    if (field_element.tagName === "SELECT") {
                        const first_option = Array.from(field_element.options).find(
                            (option) => (option.value || "").trim() !== ""
                        );
                        if (first_option) {
                            field_element.value = first_option.value;
                        }
                        continue;
                    }
                    field_element.value = "sample_value";
                    apply_compact_width_to_input(field_element);
                }
            }
        }
    });

    const post_test_action = async (row_element, action_path) => {
        const low_test_started_cell = row_element.querySelector(".low_test_started_at_cell");
        const low_test_ended_cell = row_element.querySelector(".low_test_ended_at_cell");
        const high_test_started_cell = row_element.querySelector(".high_test_started_at_cell");
        const high_test_ended_cell = row_element.querySelector(".high_test_ended_at_cell");

        if (action_path === "low_test/end") {
            const started_at = parse_datetime_from_cell(low_test_started_cell);
            if (!started_at) {
                alert("저온시험 시작 시간이 없습니다. 먼저 저온시험 시작 버튼을 눌러주세요.");
                return;
            }
            if (new Date() < started_at) {
                alert("저온시험 종료 시간은 시작 시간보다 빠를 수 없습니다. 시작 시간을 먼저 확인해 주세요.");
                return;
            }
        }
        if (action_path === "high_test/end") {
            const started_at = parse_datetime_from_cell(high_test_started_cell);
            if (!started_at) {
                alert("고온시험 시작 시간이 없습니다. 먼저 고온시험 시작 버튼을 눌러주세요.");
                return;
            }
            if (new Date() < started_at) {
                alert("고온시험 종료 시간은 시작 시간보다 빠를 수 없습니다. 시작 시간을 먼저 확인해 주세요.");
                return;
            }
        }

        if (action_path === "low_test/start") {
            set_timestamp_cell(low_test_started_cell, get_now_timestamp_info());
            set_completion_flag(row_element, "lowTestStartedDone", true);
        } else if (action_path === "low_test/end") {
            set_timestamp_cell(low_test_ended_cell, get_now_timestamp_info());
            set_completion_flag(row_element, "lowTestEndedDone", true);
        } else if (action_path === "high_test/start") {
            set_timestamp_cell(high_test_started_cell, get_now_timestamp_info());
            set_completion_flag(row_element, "highTestStartedDone", true);
        } else if (action_path === "high_test/end") {
            set_timestamp_cell(high_test_ended_cell, get_now_timestamp_info());
            set_completion_flag(row_element, "highTestEndedDone", true);
        }
        render_delta_from_timestamps(row_element, "low_test");
        render_delta_from_timestamps(row_element, "high_test");
        update_test_action_buttons(row_element);
    };

    const bind_row_actions = (row_element) => {
        const timestamp_inputs = row_element.querySelectorAll(".test_timestamp_input");
        for (const timestamp_input of timestamp_inputs) {
            timestamp_input.addEventListener("input", () => {
                delete timestamp_input.dataset.iso;
                render_delta_from_timestamps(row_element, "low_test");
                render_delta_from_timestamps(row_element, "high_test");
                update_test_action_buttons(row_element);
            });
        }

        render_delta_from_timestamps(row_element, "low_test");
        render_delta_from_timestamps(row_element, "high_test");
        update_test_action_buttons(row_element);

        row_element
            .querySelector(".low_test_start_button")
            .addEventListener("click", async () => post_test_action(row_element, "low_test/start"));
        row_element
            .querySelector(".low_test_end_button")
            .addEventListener("click", async () => post_test_action(row_element, "low_test/end"));
        row_element
            .querySelector(".high_test_start_button")
            .addEventListener("click", async () => post_test_action(row_element, "high_test/start"));
        row_element
            .querySelector(".high_test_end_button")
            .addEventListener("click", async () => post_test_action(row_element, "high_test/end"));
    };

    add_row_button.addEventListener("click", () => {
        clear_non_modal_notice();
        const editable_rows = list_editable_rows();
        const row_element = create_row_element();
        if (editable_rows.length > 0) {
            const last_row = editable_rows[editable_rows.length - 1];
            const source_fields = last_row.querySelectorAll("[data-field]");
            for (const source_field of source_fields) {
                const field_name = source_field.dataset.field;
                row_element.querySelector(`[data-field="${field_name}"]`).value = source_field.value;
            }
        }
        tester_grid_body.appendChild(row_element);
        bind_compact_width_behavior(row_element);
        bind_row_actions(row_element);
    });

    delete_selected_rows_button.addEventListener("click", () => {
        clear_non_modal_notice();
        const selected_rows = list_selected_rows();
        if (selected_rows.length === 0) {
            alert("선택한 행이 없습니다.");
            return;
        }
        for (const row_element of selected_rows) {
            const existing_id = Number((row_element.dataset.id || "").trim());
            if (Number.isInteger(existing_id) && existing_id > 0) {
                pending_deleted_row_ids.add(existing_id);
            }
            row_element.remove();
        }
    });

    select_all_rows_button.addEventListener("click", () => {
        clear_non_modal_notice();
        const editable_rows = list_editable_rows();
        for (const row_element of editable_rows) {
            const checkbox = row_element.querySelector(".row_select_checkbox");
            if (checkbox) {
                checkbox.checked = true;
            }
        }
    });

    save_all_rows_button.addEventListener("click", async () => {
        const editable_rows = list_editable_rows();
        const submission_id_for_save = generate_uuid_v7();
        const validation_messages = [];
        for (let index = 0; index < editable_rows.length; index += 1) {
            const row_element = editable_rows[index];
            for (const field of time_field_definitions) {
                const input_element = row_element.querySelector(field.selector);
                const trimmed_value = trim_timestamp_input(input_element);
                if (!is_timestamp_format_valid(trimmed_value)) {
                    alert(
                        `입력제안: ${index + 1}행 ${field.label} 컬럼의 시간포멧이 맞지 않습니다. ${accepted_time_format_hint} 형식으로 수정 부탁드립니다.`
                    );
                    return;
                }
            }
        }

        for (let index = 0; index < editable_rows.length; index += 1) {
            const missing_columns = get_missing_column_descriptions(editable_rows[index]);
            if (missing_columns.length > 0) {
                validation_messages.push(`${index + 1}행: ${missing_columns.join(", ")} 미입력`);
            }
        }

        if (validation_messages.length > 0) {
            render_non_modal_notice(validation_messages, "error");
            return;
        }

        const rows_payload = [];
        for (let index = 0; index < editable_rows.length; index += 1) {
            const row_payload = build_upsert_payload(editable_rows[index]);
            row_payload.submission_id = submission_id_for_save;
            const has_any_value =
                !!row_payload.key_1 ||
                !!row_payload.key_2 ||
                !!row_payload.key_3 ||
                field_names.some((field_name) => String(row_payload[field_name] || "").trim() !== "") ||
                !!row_payload.low_test_started_at ||
                !!row_payload.low_test_ended_at ||
                !!row_payload.high_test_started_at ||
                !!row_payload.high_test_ended_at ||
                !!row_payload.low_test_delta ||
                !!row_payload.high_test_delta;
            if (has_any_value) {
                rows_payload.push(row_payload);
            }
        }

        try {
            const response = await fetch("/tester/rows/save_all", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    rows: rows_payload,
                    delete_row_ids: Array.from(pending_deleted_row_ids),
                }),
            });
            if (!response.ok) {
                alert(await read_error_detail(response));
                return;
            }
            pending_deleted_row_ids.clear();
        } catch (_error) {
            alert("모든 행 저장 중 네트워크 오류가 발생했습니다.");
            return;
        }
        render_non_modal_notice(["모든 행 저장이 완료되었습니다."], "success");
        window.location.reload();
    });

    const existing_rows = tester_grid_body.querySelectorAll("tr.editable_row");
    for (const row_element of existing_rows) {
        bind_compact_width_behavior(row_element);
        bind_row_actions(row_element);
    }
})();

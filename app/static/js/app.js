(() => {
    const tester_grid_body = document.getElementById("tester_grid_body");
    const add_row_button = document.getElementById("add_row_button");

    if (!tester_grid_body || !add_row_button) {
        return;
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

    const update_test_action_buttons = (row_element) => {
        const has_id = !!row_element.dataset.id;
        if (!has_id) {
            set_action_buttons_disabled(row_element, true);
            return;
        }

        const low_test_started = !!row_element.querySelector(".low_test_started_at_cell").textContent.trim();
        const low_test_ended = !!row_element.querySelector(".low_test_ended_at_cell").textContent.trim();
        const high_test_started = !!row_element.querySelector(".high_test_started_at_cell").textContent.trim();
        const high_test_ended = !!row_element.querySelector(".high_test_ended_at_cell").textContent.trim();

        row_element.querySelector(".low_test_start_button").disabled = low_test_started;
        row_element.querySelector(".low_test_end_button").disabled = !low_test_started || low_test_ended;
        row_element.querySelector(".high_test_start_button").disabled = high_test_started;
        row_element.querySelector(".high_test_end_button").disabled = !high_test_started || high_test_ended;
    };

    const create_row_element = () => {
        const row_element = document.createElement("tr");
        row_element.className = "editable_row";
        row_element.dataset.id = "";
        row_element.innerHTML = `
            <td class="id_cell hidden_id_column"></td>
            <td><input data-field="key_1" value=""></td>
            <td><input data-field="key_2" value=""></td>
            <td><input data-field="key_3" value=""></td>
            <td><input data-field="field_01" value=""></td>
            <td><input data-field="field_02" value=""></td>
            <td><input data-field="field_03" value=""></td>
            <td><input data-field="field_04" value=""></td>
            <td><input data-field="field_05" value=""></td>
            <td><input data-field="field_06" value=""></td>
            <td><input data-field="field_07" value=""></td>
            <td><input data-field="field_08" value=""></td>
            <td><input data-field="field_09" value=""></td>
            <td><input data-field="field_10" value=""></td>
            <td class="low_test_started_at_cell"></td>
            <td class="low_test_ended_at_cell"></td>
            <td class="low_test_delta_cell"></td>
            <td class="high_test_started_at_cell"></td>
            <td class="high_test_ended_at_cell"></td>
            <td class="high_test_delta_cell"></td>
            <td>
                <button type="button" class="upsert_button">저장</button>
                <button type="button" class="low_test_start_button">저온시험 시작</button>
                <button type="button" class="low_test_end_button">저온시험 종료</button>
                <button type="button" class="high_test_start_button">고온시험 시작</button>
                <button type="button" class="high_test_end_button">고온시험 종료</button>
            </td>
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

        return payload;
    };

    const post_test_action = async (row_element, action_path) => {
        const row_id = row_element.dataset.id;
        if (!row_id) {
            alert("먼저 행을 저장해 id를 생성해주세요.");
            return;
        }

        try {
            const response = await fetch(`/test_result/${row_id}/${action_path}`, {
                method: "POST",
            });
            if (!response.ok) {
                alert(await read_error_detail(response));
                return;
            }

            const payload = await response.json();
            if (action_path === "low_test/start") {
                row_element.querySelector(".low_test_started_at_cell").textContent =
                    payload.low_test_started_at || "";
            } else if (action_path === "low_test/end") {
                row_element.querySelector(".low_test_ended_at_cell").textContent =
                    payload.low_test_ended_at || "";
                row_element.querySelector(".low_test_delta_cell").textContent =
                    payload.low_test_delta || "";
            } else if (action_path === "high_test/start") {
                row_element.querySelector(".high_test_started_at_cell").textContent =
                    payload.high_test_started_at || "";
            } else if (action_path === "high_test/end") {
                row_element.querySelector(".high_test_ended_at_cell").textContent =
                    payload.high_test_ended_at || "";
                row_element.querySelector(".high_test_delta_cell").textContent =
                    payload.high_test_delta || "";
            }
            update_test_action_buttons(row_element);
        } catch (_error) {
            alert("네트워크 오류가 발생했습니다.");
        }
    };

    const bind_row_actions = (row_element) => {
        update_test_action_buttons(row_element);

        row_element.querySelector(".upsert_button").addEventListener("click", async () => {
            const payload = build_upsert_payload(row_element);
            if (!payload.key_1 || !payload.key_2 || !payload.key_3) {
                alert("key_1, key_2, key_3는 필수입니다.");
                return;
            }

            try {
                const response = await fetch("/tester/rows/upsert", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                if (!response.ok) {
                    alert(await read_error_detail(response));
                    return;
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
            } catch (_error) {
                alert("네트워크 오류가 발생했습니다.");
            }
        });

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
        const no_rows_placeholder = tester_grid_body.querySelector("tr td[colspan='21']");
        if (no_rows_placeholder) {
            no_rows_placeholder.parentElement.remove();
        }
        const row_element = create_row_element();
        tester_grid_body.prepend(row_element);
        bind_compact_width_behavior(row_element);
        bind_row_actions(row_element);
    });

    const existing_rows = tester_grid_body.querySelectorAll("tr.editable_row");
    for (const row_element of existing_rows) {
        bind_compact_width_behavior(row_element);
        bind_row_actions(row_element);
    }
})();

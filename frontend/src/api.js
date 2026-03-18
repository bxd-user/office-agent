export async function runTask({ instruction, files }) {
    const formData = new FormData();
    formData.append("task_type", "agent_autonomous");
    formData.append("instruction", instruction);
    (files || []).forEach((file) => {
        formData.append("files", file);
    });

    const res = await fetch("http://127.0.0.1:8000/api/tasks/execute", {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        let detail = "请求失败";
        try {
            const payload = await res.json();
            detail = payload?.detail || payload?.message || detail;
        } catch {
            detail = `请求失败(${res.status})`;
        }
        throw new Error(detail);
    }

    return await res.json();
}
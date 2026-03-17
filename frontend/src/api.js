export async function runTask({ instruction, excelFile, wordFile }) {
    const formData = new FormData();
    formData.append("instruction", instruction);
    formData.append("excel_file", excelFile);
    formData.append("word_file", wordFile);

    const res = await fetch("http://127.0.0.1:8000/api/tasks/run", {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        throw new Error("请求失败");
    }

    return await res.json();
}
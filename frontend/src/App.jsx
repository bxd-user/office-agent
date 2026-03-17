import React, { useState } from "react";

export default function App() {
    const [instruction, setInstruction] = useState("把 Excel 第一行数据填入 Word 审核表");
    const [excelFile, setExcelFile] = useState(null);
    const [wordFile, setWordFile] = useState(null);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    async function handleSubmit() {
        if (!excelFile || !wordFile) {
            alert("请先上传 Excel 和 Word");
            return;
        }

        setLoading(true);

        const formData = new FormData();
        formData.append("instruction", instruction);
        formData.append("excel_file", excelFile);
        formData.append("word_file", wordFile);

        try {
            const res = await fetch("http://127.0.0.1:8000/api/tasks/run", {
                method: "POST",
                body: formData,
            });

            const data = await res.json();
            setResult(data);
        } catch (err) {
            alert("请求失败：" + err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ maxWidth: 800, margin: "40px auto", fontFamily: "sans-serif" }}>
            <h1>Office Agent V1</h1>

            <div style={{ marginBottom: 16 }}>
                <div>指令</div>
                <textarea
                    value={instruction}
                    onChange={(e) => setInstruction(e.target.value)}
                    rows={4}
                    style={{ width: "100%" }}
                />
            </div>

            <div style={{ marginBottom: 16 }}>
                <div>上传 Excel</div>
                <input type="file" accept=".xlsx" onChange={(e) => setExcelFile(e.target.files[0])} />
            </div>

            <div style={{ marginBottom: 16 }}>
                <div>上传 Word</div>
                <input type="file" accept=".docx" onChange={(e) => setWordFile(e.target.files[0])} />
            </div>

            <button onClick={handleSubmit} disabled={loading}>
                {loading ? "生成中..." : "执行"}
            </button>

            {result && (
                <div style={{ marginTop: 24 }}>
                    <h2>结果</h2>
                    <div>{result.message}</div>

                    <h3>字段映射</h3>
                    <pre>{JSON.stringify(result.mapping, null, 2)}</pre>

                    <h3>日志</h3>
                    <pre>{result.logs.join("\n")}</pre>

                    <a
                        href={`http://127.0.0.1:8000${result.download_url}`}
                        target="_blank"
                        rel="noreferrer"
                    >
                        下载生成的 Word
                    </a>
                </div>
            )}
        </div>
    );
}
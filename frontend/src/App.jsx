import React, { useState } from "react";
import { runTask } from "./api";

export default function App() {
    const [instruction, setInstruction] = useState("请根据文件内容自动规划步骤并完成文档处理任务");
    const [files, setFiles] = useState([]);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    async function handleSubmit() {
        if (!files.length) {
            alert("请至少上传一个文件");
            return;
        }

        setLoading(true);

        try {
            const data = await runTask({ instruction, files });
            setResult(data);
        } catch (err) {
            alert("请求失败：" + err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ maxWidth: 800, margin: "40px auto", fontFamily: "sans-serif" }}>
            <h1>Office Agent V2</h1>

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
                <div>上传文件（支持 Excel / Word，可多选）</div>
                <input
                    type="file"
                    multiple
                    accept=".xlsx,.xlsm,.xltx,.xltm,.csv,.tsv,.docx,.docm,.dotx,.dotm"
                    onChange={(e) => setFiles(Array.from(e.target.files || []))}
                />
            </div>

            {!!files.length && (
                <div style={{ marginBottom: 16 }}>
                    已选择 {files.length} 个文件：{files.map((file) => file.name).join("，")}
                </div>
            )}

            <button onClick={handleSubmit} disabled={loading}>
                {loading ? "生成中..." : "执行"}
            </button>

            {result && (
                <div style={{ marginTop: 24 }}>
                    <h2>结果</h2>
                    <div>{result.message || "执行完成"}</div>

                    <h3>本次执行结果（看到了什么）</h3>
                    {Array.isArray(result.execution_observation) && result.execution_observation.length > 0 ? (
                        <pre style={{ whiteSpace: "pre-wrap" }}>{result.execution_observation.join("\n")}</pre>
                    ) : (
                        <div>暂无执行结果摘要。</div>
                    )}

                    <h3>LLM 推理过程</h3>
                    <pre style={{ whiteSpace: "pre-wrap" }}>
                        {(Array.isArray(result.logs) ? result.logs : ["无日志"]).join("\n")}
                    </pre>

                    <h3>读到了什么</h3>
                    {Array.isArray(result.read_summaries) && result.read_summaries.length > 0 ? (
                        <pre>{JSON.stringify(result.read_summaries, null, 2)}</pre>
                    ) : (
                        <div>暂无读取摘要（请确认后端已重启到最新代码，并重新执行一次）。</div>
                    )}

                    <h3>置信度</h3>
                    <div>{result.confidence || "unknown"}</div>

                    <h3>缺失字段</h3>
                    <pre>{JSON.stringify(result.missing_fields || [], null, 2)}</pre>

                    <h3>字段映射</h3>
                    <pre>{JSON.stringify(result.mapping || {}, null, 2)}</pre>

                    <h3>最终写入上下文</h3>
                    <pre>{JSON.stringify(result.context || {}, null, 2)}</pre>

                    <h3>原始返回</h3>
                    <pre>{JSON.stringify(result, null, 2)}</pre>

                    {result.download_url ? (
                        <a
                            href={`http://127.0.0.1:8000${result.download_url}`}
                            target="_blank"
                            rel="noreferrer"
                        >
                            下载生成的 Word
                        </a>
                    ) : (
                        <div style={{ marginTop: 8 }}>本次仅完成读取分析，未生成输出文件。</div>
                    )}
                </div>
            )}
        </div>
    );
}
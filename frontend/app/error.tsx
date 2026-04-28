"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="pageStack">
      <div className="statePanel">
        <h2>页面出错</h2>
        <p>{error.message || "请稍后重试。"}</p>
        <button type="button" onClick={reset}>
          重试
        </button>
      </div>
    </section>
  );
}

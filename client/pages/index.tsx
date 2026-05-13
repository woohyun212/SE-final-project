import { useEffect, useState } from 'react';

interface HealthResponse {
  message: string;
}

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json() as Promise<HealthResponse>;
      })
      .then((data) => setHealth(data))
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
      });
  }, []);

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 640, margin: '80px auto', padding: '0 24px' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>SE Final Project</h1>
      <p style={{ fontSize: '1.25rem', color: '#555', marginBottom: '2rem' }}>Hello World</p>

      <section>
        <h2 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Backend /health</h2>
        {health !== null && (
          <pre style={{ background: '#f4f4f4', padding: '12px', borderRadius: '6px' }}>
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
        {error !== null && (
          <pre style={{ background: '#fff0f0', color: '#c00', padding: '12px', borderRadius: '6px' }}>
            Error: {error}
          </pre>
        )}
        {health === null && error === null && (
          <p style={{ color: '#888' }}>백엔드 응답 대기 중…</p>
        )}
      </section>
    </main>
  );
}

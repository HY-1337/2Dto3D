import React, { useEffect, useRef, useState } from 'react';
import Web3DScene from './components/Web3DScene';
import './index.css';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';
const WS_URL = import.meta.env.VITE_NEXUS_WS || 'ws://127.0.0.1:8765';

function Icon({ children }) {
  return <span className="icon" aria-hidden="true">{children}</span>;
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M17 8 12 3 7 8" />
      <path d="M12 3v12" />
    </svg>
  );
}

function readJson(response) {
  return response.text().then((text) => {
    try {
      return JSON.parse(text);
    } catch {
      return { raw: text };
    }
  });
}

function formatStatus(value) {
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

function App() {
  const [activePage, setActivePage] = useState('image');
  const [logs, setLogs] = useState([]);
  const [ws, setWs] = useState(null);
  const [wsState, setWsState] = useState('disconnected');
  const [chatInput, setChatInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  const [backgroundPath, setBackgroundPath] = useState(null);
  const [avatars, setAvatars] = useState([]);
  const [showGrid, setShowGrid] = useState(true);
  const [showControls, setShowControls] = useState(true);
  const [manualOffset, setManualOffset] = useState({ x: 0, y: 0, z: 0 });
  const [sceneOffset, setSceneOffset] = useState({ x: 0, y: 0, z: 0 });
  const [manualRotation, setManualRotation] = useState({ x: 0, y: 0, z: 0 });
  const [sceneRotation, setSceneRotation] = useState({ x: 0, y: 0, z: 0 });
  const [controlTarget, setControlTarget] = useState('avatar');

  const [imagePrompt, setImagePrompt] = useState('一个戴耳机的蓝色小猫潮玩公仔，正面全身，干净白底，适合转成3D模型');
  const [imageStyle, setImageStyle] = useState('chaoplay');
  const [imageSize, setImageSize] = useState('1024x1024');
  const [imageExtra, setImageExtra] = useState('');
  const [imageStatus, setImageStatus] = useState('Ready.');
  const [generatedImage, setGeneratedImage] = useState(null);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);

  const [modelFile, setModelFile] = useState(null);
  const [modelJob, setModelJob] = useState(null);
  const [modelStatus, setModelStatus] = useState('Ready.');
  const [isModelRunning, setIsModelRunning] = useState(false);
  const [modelProfile, setModelProfile] = useState('print');
  const [modelBackend, setModelBackend] = useState('local');
  const [pdfPage, setPdfPage] = useState(1);

  const fileInputRef = useRef(null);
  const modelInputRef = useRef(null);
  const logsEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const avatarStatesRef = useRef({});
  const sceneObjectsRef = useRef({});
  const pollTokenRef = useRef(0);

  const addLog = (message) => {
    setLogs((prev) => [...prev.slice(-120), { time: new Date().toLocaleTimeString(), message }]);
  };

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    setWs(socket);
    setWsState('connecting');

    socket.onopen = () => {
      setWsState('connected');
      addLog('Connected to Nexus interactive server.');
    };
    socket.onclose = () => {
      setWsState('disconnected');
      addLog('Disconnected from Nexus interactive server.');
    };
    socket.onerror = () => {
      setWsState('error');
      addLog('Nexus WebSocket connection failed. Start backend2/interactive_server.py first.');
    };
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const actions = Array.isArray(payload) ? payload : [payload];
        actions.forEach(handleNexusAction);
      } catch {
        addLog(`[AI] ${event.data}`);
      }
    };

    navigator.mediaDevices?.getUserMedia({ audio: true })
      .then((stream) => {
        const recorder = new MediaRecorder(stream);
        mediaRecorderRef.current = recorder;
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) audioChunksRef.current.push(event.data);
        };
        recorder.onstop = transcribeRecording;
      })
      .catch((error) => addLog(`Microphone unavailable: ${error.message}`));

    return () => socket.close();
  }, []);

  const handleNexusAction = (data) => {
    if (data.action === 'load_scene') {
      setBackgroundPath(data.path);
      addLog('[AI] Loaded scene background.');
      return;
    }
    if (data.action === 'load_avatar') {
      setAvatars((prev) => [...prev, { path: data.path, positionX: prev.length * 2 }]);
      addLog('[AI] Loaded avatar into the 3D scene.');
      return;
    }
    if (data.action === 'move_to') {
      setAvatars((prev) => prev.map((avatar, index) => (
        !data.target || data.target === `Avatar ${index + 1}`
          ? { ...avatar, destination: data.destination, trigger: 'Walk', audioBase64: data.audio_base64 }
          : avatar
      )));
      addLog(`[AI] ${data.reply || 'Moving avatar.'}`);
      return;
    }
    if (data.action === 'dynamic_code' || data.action === 'chat') {
      setAvatars((prev) => prev.map((avatar, index) => (
        !data.target || data.target === `Avatar ${index + 1}`
          ? {
              ...avatar,
              trigger: data.trigger || 'Idle',
              audioBase64: data.audio_base64,
              dynamicCode: data.code || null,
              destination: null,
            }
          : avatar
      )));
      addLog(`[AI] ${data.reply || 'Action received.'}`);
      return;
    }
    addLog(`[AI] ${data.reply || JSON.stringify(data)}`);
  };

  const transcribeRecording = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
    audioChunksRef.current = [];
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice.webm');
    addLog('Transcribing voice command...');

    try {
      const response = await fetch(`${API_BASE}/api/images/transcribe`, {
        method: 'POST',
        body: formData,
      });
      const data = await readJson(response);
      if (!response.ok) {
        addLog(`Voice transcription failed: ${JSON.stringify(data)}`);
        return;
      }
      setChatInput((prev) => `${prev}${data.text}`);
      addLog(`Voice text: ${data.text}`);
    } catch (error) {
      addLog(`Voice request failed: ${error.message}`);
    }
  };

  const toggleRecording = () => {
    if (!mediaRecorderRef.current) {
      addLog('Microphone is not ready.');
      return;
    }
    if (isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      return;
    }
    audioChunksRef.current = [];
    mediaRecorderRef.current.start();
    setIsRecording(true);
    addLog('Recording voice command...');
  };

  const sendChat = (event) => {
    event.preventDefault();
    if (!chatInput.trim()) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      addLog('Nexus server is not connected.');
      return;
    }
    ws.send(JSON.stringify({
      text: chatInput,
      sceneState: {
        avatars: avatarStatesRef.current,
        objects: sceneObjectsRef.current,
      },
    }));
    addLog(`[You] ${chatInput}`);
    setChatInput('');
  };

  const handleLocalModel = (selectedFile) => {
    if (!selectedFile) return;
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (!['obj', '3mf', 'glb', 'gltf', 'fbx'].includes(ext)) {
      addLog('Only OBJ, 3MF, GLB, GLTF, and FBX files can be loaded into the motion page.');
      return;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setAvatars((prev) => [...prev, { path: objectUrl, positionX: prev.length * 2 }]);
    addLog(`Loaded ${selectedFile.name} into the 3D scene.`);
  };

  const handleGenerateImage = async (event) => {
    event.preventDefault();
    const [width, height] = imageSize.split('x').map(Number);
    setIsGeneratingImage(true);
    setImageStatus('Generating image...');

    try {
      const response = await fetch(`${API_BASE}/api/images/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: imagePrompt,
          style: imageStyle,
          width,
          height,
          extra_suffix: imageExtra,
        }),
      });
      const data = await readJson(response);
      if (!response.ok) {
        setImageStatus(formatStatus(data));
        return;
      }
      const url = `${API_BASE}${data.image_url}?ts=${Date.now()}`;
      setGeneratedImage({ ...data, url });
      setImageStatus(formatStatus(data));
    } catch (error) {
      setImageStatus(`Request failed: ${error.message}`);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const sendGeneratedToModel = async () => {
    if (!generatedImage) return;
    setActivePage('model');
    setModelStatus('Preparing generated image...');
    const response = await fetch(generatedImage.url, { cache: 'no-store' });
    const blob = await response.blob();
    const filename = generatedImage.image_url.split('/').pop() || 'generated.png';
    setModelFile(new File([blob], filename, { type: blob.type || 'image/png' }));
    setModelStatus('Generated image is ready for 2D to 3D.');
  };

  const submitModelJob = async (event) => {
    event.preventDefault();
    if (!modelFile) {
      setModelStatus('Choose an image, SVG, or PDF first.');
      return;
    }
    const formData = new FormData();
    formData.append('file', modelFile);
    formData.append('profile', modelProfile);
    formData.append('backend', modelBackend);
    formData.append('pdf_page', String(pdfPage));

    setIsModelRunning(true);
    setModelStatus('Uploading model job...');
    setModelJob(null);

    try {
      const response = await fetch(`${API_BASE}/api/jobs`, { method: 'POST', body: formData });
      const data = await readJson(response);
      if (!response.ok) {
        setModelStatus(formatStatus(data));
        setIsModelRunning(false);
        return;
      }
      setModelJob(data);
      setModelStatus(formatStatus(data));
      const token = ++pollTokenRef.current;
      pollModelJob(data.job_id, token);
    } catch (error) {
      setModelStatus(`Request failed: ${error.message}`);
      setIsModelRunning(false);
    }
  };

  const pollModelJob = async (jobId, token) => {
    try {
      const response = await fetch(`${API_BASE}/api/jobs/${jobId}?ts=${Date.now()}`, { cache: 'no-store' });
      const data = await readJson(response);
      if (token !== pollTokenRef.current) return;
      setModelJob(data);
      setModelStatus(formatStatus(data));
      if (data.status === 'done' || data.status === 'failed') {
        setIsModelRunning(false);
        return;
      }
      window.setTimeout(() => pollModelJob(jobId, token), 1500);
    } catch (error) {
      setModelStatus(`Polling failed: ${error.message}`);
      setIsModelRunning(false);
    }
  };

  const loadPreviewIntoScene = () => {
    if (!modelJob?.job_id) return;
    const url = `${API_BASE}/api/jobs/${modelJob.job_id}/preview?ts=${Date.now()}`;
    setAvatars((prev) => [...prev, { path: url, positionX: prev.length * 2 }]);
    setActivePage('motion');
    addLog('Loaded generated GLB preview into the motion page.');
  };

  const openBambu = async () => {
    if (!modelJob?.job_id) return;
    const response = await fetch(`${API_BASE}/api/jobs/${modelJob.job_id}/open-bambu`, { method: 'POST' });
    setModelStatus(formatStatus(await readJson(response)));
  };

  const handleReachDestination = (index) => {
    setAvatars((prev) => prev.map((avatar, current) => (
      current === index ? { ...avatar, destination: null, trigger: 'Idle' } : avatar
    )));
  };

  const done = modelJob?.status === 'done';

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1 className="app-title">Nexus 3D</h1>
          <p className="app-subtitle">Text to image, image to 3D, then bring the model to life.</p>
        </div>
        <nav className="page-tabs" aria-label="Workspace pages">
          <button className={activePage === 'image' ? 'active' : ''} onClick={() => setActivePage('image')}>文生图</button>
          <button className={activePage === 'model' ? 'active' : ''} onClick={() => setActivePage('model')}>2D 转 3D</button>
          <button className={activePage === 'motion' ? 'active' : ''} onClick={() => setActivePage('motion')}>3D 动起来</button>
        </nav>
      </header>

      {activePage === 'motion' && (
        <main className="motion-layout">
          <aside className="left-stack">
            <section className="glass-panel compact-panel">
              <div className="panel-title">
                <h2>模型与服务</h2>
                <span className={`connection ${wsState}`}>{wsState}</span>
              </div>
              <div
                className="drop-zone"
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  handleLocalModel(event.dataTransfer.files?.[0]);
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  hidden
                  accept=".obj,.3mf,.glb,.gltf,.fbx"
                  onChange={(event) => handleLocalModel(event.target.files?.[0])}
                />
                <div className="drop-icon"><UploadIcon /></div>
                <h3>加载 3D 模型</h3>
                <p>支持 OBJ、3MF、GLB、GLTF、FBX</p>
              </div>
              <div className="button-row">
                <button className="btn ghost" onClick={() => setShowGrid((value) => !value)}>
                  {showGrid ? '隐藏网格' : '显示网格'}
                </button>
                <button className="btn ghost" onClick={() => setShowControls((value) => !value)}>
                  {showControls ? '隐藏控制器' : '显示控制器'}
                </button>
              </div>
            </section>

            <section className="glass-panel compact-panel">
              <h2>AI 指令</h2>
              <form className="chat-form" onSubmit={sendChat}>
                <textarea
                  className="input-field"
                  rows="4"
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="例如：让 1 号角色向左走两步，然后挥手介绍自己"
                />
                <div className="button-row">
                  <button type="button" className={`btn ${isRecording ? 'danger' : 'secondary'}`} onClick={toggleRecording}>
                    {isRecording ? '停止录音' : '语音输入'}
                  </button>
                  <button className="btn" type="submit">发送</button>
                </div>
              </form>
            </section>
          </aside>

          <section className="scene-panel">
            <Web3DScene
              backgroundPath={backgroundPath}
              avatars={avatars}
              showGrid={showGrid}
              manualOffset={manualOffset}
              sceneOffset={sceneOffset}
              manualRotation={manualRotation}
              sceneRotation={sceneRotation}
              onReachDestination={handleReachDestination}
              avatarStatesRef={avatarStatesRef}
              sceneObjectsRef={sceneObjectsRef}
            />

            {showControls && (
              <div className="control-pad">
                <div className="segmented">
                  <button className={controlTarget === 'avatar' ? 'active' : ''} onClick={() => setControlTarget('avatar')}>数字人</button>
                  <button className={controlTarget === 'scene' ? 'active' : ''} onClick={() => setControlTarget('scene')}>场景</button>
                </div>
                <div className="dpad">
                  <button onClick={() => controlTarget === 'avatar' ? setManualOffset((p) => ({ ...p, y: p.y + 0.5 })) : setSceneOffset((p) => ({ ...p, y: p.y - 0.5 }))}>上</button>
                  <button onClick={() => controlTarget === 'avatar' ? setManualOffset((p) => ({ ...p, x: p.x - 0.5 })) : setSceneOffset((p) => ({ ...p, x: p.x + 0.5 }))}>左</button>
                  <button onClick={() => {
                    if (controlTarget === 'avatar') {
                      setManualOffset({ x: 0, y: 0, z: 0 });
                      setManualRotation({ x: 0, y: 0, z: 0 });
                    } else {
                      setSceneOffset({ x: 0, y: 0, z: 0 });
                      setSceneRotation({ x: 0, y: 0, z: 0 });
                    }
                  }}>重置</button>
                  <button onClick={() => controlTarget === 'avatar' ? setManualOffset((p) => ({ ...p, x: p.x + 0.5 })) : setSceneOffset((p) => ({ ...p, x: p.x - 0.5 }))}>右</button>
                  <button onClick={() => controlTarget === 'avatar' ? setManualOffset((p) => ({ ...p, y: p.y - 0.5 })) : setSceneOffset((p) => ({ ...p, y: p.y + 0.5 }))}>下</button>
                </div>
              </div>
            )}

            <div className="log-console">
              {logs.length === 0 && <span className="muted">Waiting for commands...</span>}
              {logs.map((log, index) => (
                <div key={`${log.time}-${index}`}>
                  <span>[{log.time}]</span> {log.message}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </section>
        </main>
      )}

      {activePage === 'image' && (
        <main className="two-column-page">
          <form className="glass-panel form-panel" onSubmit={handleGenerateImage}>
            <h2><Icon>✦</Icon> 文字生成图片</h2>
            <label className="input-label">角色描述</label>
            <textarea className="input-field" rows="6" value={imagePrompt} onChange={(event) => setImagePrompt(event.target.value)} />
            <div className="form-grid">
              <div>
                <label className="input-label">风格</label>
                <select className="input-field" value={imageStyle} onChange={(event) => setImageStyle(event.target.value)}>
                  <option value="chaoplay">潮玩</option>
                  <option value="perler">像素拼豆</option>
                  <option value="minimal">极简</option>
                </select>
              </div>
              <div>
                <label className="input-label">尺寸</label>
                <select className="input-field" value={imageSize} onChange={(event) => setImageSize(event.target.value)}>
                  <option value="1024x1024">1024 x 1024</option>
                  <option value="1024x1792">1024 x 1792</option>
                  <option value="1792x1024">1792 x 1024</option>
                </select>
              </div>
            </div>
            <label className="input-label">补充要求</label>
            <input className="input-field" value={imageExtra} onChange={(event) => setImageExtra(event.target.value)} placeholder="例如：更像软胶玩具，没有文字" />
            <div className="button-row">
              <button className="btn" disabled={isGeneratingImage}>{isGeneratingImage ? '生成中...' : '生成图片'}</button>
              <button className="btn ghost" type="button" disabled={!generatedImage} onClick={sendGeneratedToModel}>送去 2D 转 3D</button>
            </div>
            <pre className="status-box">{imageStatus}</pre>
          </form>

          <section className="glass-panel result-panel">
            <h2>图片预览</h2>
            <div className="image-preview">
              {generatedImage ? <img src={generatedImage.url} alt="Generated character concept" /> : <span>生成结果会显示在这里</span>}
            </div>
            {generatedImage && (
              <a className="text-link" href={generatedImage.url} target="_blank" rel="noreferrer">打开原图</a>
            )}
          </section>
        </main>
      )}

      {activePage === 'model' && (
        <main className="two-column-page">
          <form className="glass-panel form-panel" onSubmit={submitModelJob}>
            <h2><Icon>⬢</Icon> 2D 图片转 3D</h2>
            <div
              className={`drop-zone ${modelFile ? 'active' : ''}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                setModelFile(event.dataTransfer.files?.[0] || null);
              }}
              onClick={() => modelInputRef.current?.click()}
            >
              <input
                ref={modelInputRef}
                type="file"
                hidden
                accept=".webp,.jpg,.jpeg,.png,.svg,.pdf"
                onChange={(event) => setModelFile(event.target.files?.[0] || null)}
              />
              <div className="drop-icon"><UploadIcon /></div>
              <h3>{modelFile ? modelFile.name : '上传图片、SVG 或 PDF'}</h3>
              <p>输出 OBJ ZIP、3MF 和 GLB 预览</p>
            </div>
            <div className="form-grid">
              <div>
                <label className="input-label">PDF 页码</label>
                <input className="input-field" type="number" min="1" value={pdfPage} onChange={(event) => setPdfPage(event.target.value)} />
              </div>
              <div>
                <label className="input-label">用途</label>
                <select className="input-field" value={modelProfile} onChange={(event) => setModelProfile(event.target.value)}>
                  <option value="print">3D 打印</option>
                  <option value="render">渲染预览</option>
                </select>
              </div>
            </div>
            <label className="input-label">建模后端</label>
            <select className="input-field" value={modelBackend} onChange={(event) => setModelBackend(event.target.value)}>
              <option value="local">local / TripoSR</option>
              <option value="cloud_stub">cloud_stub</option>
            </select>
            <div className="button-row">
              <button className="btn" disabled={isModelRunning}>{isModelRunning ? '建模中...' : '开始建模'}</button>
              <button className="btn ghost" type="button" disabled={!done} onClick={loadPreviewIntoScene}>进入 3D 动起来</button>
              <button className="btn secondary" type="button" disabled={!done} onClick={openBambu}>打开 Bambu</button>
            </div>
            <pre className="status-box">{modelStatus}</pre>
          </form>

          <section className="glass-panel result-panel">
            <h2>3D 输出</h2>
            <div className="output-actions">
              <a className={!done ? 'disabled-link' : ''} href={done ? `${API_BASE}/api/jobs/${modelJob.job_id}/preview` : '#'} target="_blank" rel="noreferrer">GLB 预览</a>
              <a className={!done ? 'disabled-link' : ''} href={done ? `${API_BASE}/api/jobs/${modelJob.job_id}/download?format=obj` : '#'}>OBJ ZIP</a>
              <a className={!done ? 'disabled-link' : ''} href={done ? `${API_BASE}/api/jobs/${modelJob.job_id}/download?format=3mf` : '#'}>3MF</a>
            </div>
            <div className="progress-readout">
              <strong>{modelJob?.status || 'idle'}</strong>
              <span>{Math.round((modelJob?.progress || 0) * 100)}%</span>
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

export default App;

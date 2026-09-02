"""Interfaz autocontenida del asistente local, sin recursos remotos."""

from __future__ import annotations

import html
import json

STYLES = r"""
:root {
  color-scheme: dark;
  --bg: #171415;
  --surface: #221d1e;
  --surface-raised: #2a2324;
  --surface-soft: #312829;
  --text: #fff9f7;
  --muted: #bcaeb0;
  --muted-strong: #d9ccce;
  --line: #4a3a3c;
  --line-soft: #382d2f;
  --red: #e3261e;
  --red-bright: #ff3b31;
  --red-dark: #8c1715;
  --green: #72d89b;
  --amber: #f3c76b;
  --shadow: 0 32px 90px #00000066;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* { box-sizing: border-box; }

html { min-width: 320px; background: var(--bg); }

body {
  margin: 0;
  min-height: 100vh;
  background:
    radial-gradient(circle at 14% 18%, #a718143d 0, transparent 34rem),
    radial-gradient(circle at 87% 42%, #8f1b172b 0, transparent 29rem),
    linear-gradient(125deg, #261718 0%, var(--bg) 43%, #1b1718 100%);
  color: var(--text);
}

body::before {
  position: fixed;
  inset: 0;
  background-image: linear-gradient(#ffffff08 1px, transparent 1px), linear-gradient(90deg, #ffffff08 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(to bottom, #0008, transparent 82%);
  pointer-events: none;
  content: "";
}

button, input { font: inherit; }

button, a { -webkit-tap-highlight-color: transparent; }

button { color: inherit; }

a { color: var(--text); }

[hidden] { display: none !important; }

.page {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 28px;
  overflow: hidden;
}

.orb {
  position: fixed;
  border: 1px solid #ff43341f;
  border-radius: 999px;
  pointer-events: none;
}

.orb-one { top: -18rem; right: -12rem; width: 42rem; height: 42rem; }
.orb-two { bottom: -15rem; left: -12rem; width: 34rem; height: 34rem; }

.shell {
  position: relative;
  width: min(1180px, 100%);
  border: 1px solid #5a424533;
  border-radius: 28px;
  background: #1d191aeb;
  box-shadow: var(--shadow);
  overflow: hidden;
  backdrop-filter: blur(18px);
}

.topbar {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 76px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--line-soft);
  background: #181415cc;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 1px solid #ff72674d;
  border-radius: 13px 13px 17px 17px;
  background: linear-gradient(145deg, var(--red-bright), var(--red-dark));
  box-shadow: 0 8px 24px #df241d42, inset 0 1px #ffffff47;
  font-weight: 900;
  letter-spacing: -0.08em;
}

.brand-copy { display: grid; gap: 2px; }
.brand-copy strong { font-size: 15px; letter-spacing: .02em; }
.brand-copy span { color: var(--muted); font-size: 12px; }

.unofficial {
  margin-left: auto;
  border: 1px solid #7e5d614d;
  border-radius: 999px;
  padding: 7px 11px;
  color: var(--muted-strong);
  background: #ffffff08;
  font-size: 12px;
  font-weight: 750;
  letter-spacing: .04em;
  text-transform: uppercase;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.04fr) minmax(340px, .96fr);
  min-height: 670px;
}

.primary-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: clamp(38px, 6vw, 74px);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 8px;
  margin: 0 0 18px;
  color: var(--muted-strong);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.eyebrow::before {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 5px #72d89b1f;
  content: "";
}

h1, h2, p { margin-top: 0; }

h1 {
  max-width: 10ch;
  margin-bottom: 20px;
  font-size: clamp(42px, 6vw, 72px);
  line-height: .98;
  letter-spacing: -.055em;
}

h1 em { color: var(--red-bright); font-style: normal; }

.lead {
  max-width: 600px;
  margin-bottom: 26px;
  color: var(--muted-strong);
  font-size: 16px;
  line-height: 1.65;
}

.local-note {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  border: 1px solid #4e3b3e;
  border-radius: 14px;
  padding: 13px 15px;
  background: #ffffff07;
  color: var(--muted-strong);
  font-size: 13px;
  line-height: 1.5;
}

.local-note-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: #72d89b1a;
  color: var(--green);
  font-weight: 900;
}

.flow-panel {
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 22px;
  background: linear-gradient(155deg, #2c2425, #221d1e);
  box-shadow: 0 18px 45px #0004;
}

.field { display: grid; gap: 8px; margin-bottom: 16px; }
.field-label { color: var(--muted-strong); font-size: 13px; font-weight: 750; }

.input-wrap { position: relative; }

.input-icon {
  position: absolute;
  top: 50%;
  left: 15px;
  color: #947f82;
  font-size: 15px;
  font-weight: 850;
  transform: translateY(-50%);
  pointer-events: none;
}

input {
  width: 100%;
  height: 52px;
  border: 1px solid #594649;
  border-radius: 12px;
  outline: none;
  padding: 0 15px 0 43px;
  background: #181415;
  color: var(--text);
  transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
}

input::placeholder { color: #746366; }
input:hover { border-color: #74585c; }
input:focus { border-color: var(--red-bright); box-shadow: 0 0 0 4px #ff3b311f; background: #1b1617; }

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-height: 52px;
  border: 0;
  border-radius: 12px;
  padding: 0 18px;
  cursor: pointer;
  font-weight: 850;
  transition: transform .15s ease, filter .15s ease, box-shadow .15s ease;
}

.button:hover:not(:disabled) { filter: brightness(1.08); transform: translateY(-1px); }
.button:active:not(:disabled) { transform: translateY(0); }
.button:focus-visible, .league-choice:focus-visible, .text-button:focus-visible, a:focus-visible { outline: 3px solid #ff847b; outline-offset: 3px; }
.button:disabled, .league-choice:disabled { cursor: wait; opacity: .62; }

.button-primary {
  margin-top: 5px;
  background: linear-gradient(135deg, var(--red-bright), #cf1c17);
  box-shadow: 0 10px 25px #e3261e38, inset 0 1px #ffffff3d;
}

.button-danger { background: linear-gradient(135deg, #e83b32, #a51210); box-shadow: 0 10px 25px #e3261e30; }

.arrow { margin-left: auto; font-size: 20px; line-height: 1; }

.account-help {
  margin: 18px 2px 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
}

.account-help a { color: #ffc0bb; font-weight: 750; text-underline-offset: 3px; }

.section-head { margin-bottom: 18px; }
.section-head small { color: var(--red-bright); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.section-head h2 { margin: 8px 0 8px; font-size: 27px; letter-spacing: -.025em; }
.section-head p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.55; }

.choices { display: grid; gap: 10px; }

.league-choice {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 14px;
  width: 100%;
  border: 1px solid #594649;
  border-radius: 14px;
  padding: 15px;
  background: #191516;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: border-color .15s ease, background .15s ease, transform .15s ease;
}

.league-choice:hover:not(:disabled) { border-color: var(--red-bright); background: #241a1b; transform: translateY(-1px); }
.league-name { overflow: hidden; font-weight: 850; text-overflow: ellipsis; white-space: nowrap; }
.league-score { align-self: center; color: #ffc1bc; font-size: 12px; font-weight: 800; }
.league-meta { grid-column: 1 / -1; color: var(--muted); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; }

.text-button {
  margin-top: 14px;
  border: 0;
  padding: 5px 0;
  background: transparent;
  color: var(--muted-strong);
  cursor: pointer;
  font-weight: 750;
  text-decoration: underline;
  text-underline-offset: 4px;
}

.status {
  margin: 16px 0 0;
  border: 1px solid #635054;
  border-radius: 12px;
  padding: 11px 13px;
  background: #ffffff09;
  color: var(--muted-strong);
  font-size: 13px;
  line-height: 1.45;
}

.status[data-tone="error"] { border-color: #a64943; background: #8b1f1a24; color: #ffd1cd; }
.status[data-tone="success"] { border-color: #3f7e59; background: #1f6d3c24; color: #baf3cf; }

.success-mark {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  margin-bottom: 16px;
  border: 1px solid #72d89b70;
  border-radius: 17px;
  background: #72d89b1a;
  color: var(--green);
  font-size: 26px;
  font-weight: 950;
}

.success-panel h2 { margin-bottom: 9px; font-size: 29px; }
.success-panel p { color: var(--muted-strong); line-height: 1.6; }
.next-steps { display: grid; gap: 9px; margin-top: 18px; }
.next-step { display: flex; align-items: center; gap: 11px; color: var(--muted-strong); font-size: 13px; }
.next-step span { display: grid; place-items: center; flex: 0 0 auto; width: 24px; height: 24px; border-radius: 50%; background: #ffffff0d; color: #fff; font-size: 11px; font-weight: 850; }

.showcase {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  border-left: 1px solid var(--line-soft);
  padding: clamp(36px, 5vw, 64px);
  background:
    linear-gradient(160deg, #2a1c1d99, #161314e8),
    radial-gradient(circle at 80% 18%, #e3261e42, transparent 18rem);
  overflow: hidden;
}

.showcase::after {
  position: absolute;
  right: -8rem;
  bottom: -9rem;
  width: 26rem;
  height: 26rem;
  border: 1px solid #ff574b24;
  border-radius: 50%;
  content: "";
}

.showcase-content { position: relative; z-index: 1; width: min(420px, 100%); }
.showcase-kicker { color: #ff8f87; font-size: 12px; font-weight: 850; letter-spacing: .11em; text-transform: uppercase; }
.showcase h2 { margin: 12px 0 12px; font-size: clamp(30px, 4vw, 45px); line-height: 1.04; letter-spacing: -.045em; }
.showcase-copy { color: var(--muted); font-size: 14px; line-height: 1.65; }

.data-card {
  margin-top: 28px;
  border: 1px solid #6c4b4f;
  border-radius: 20px;
  padding: 18px;
  background: #1b1718e8;
  box-shadow: 0 25px 60px #0008, 0 0 35px #d3241c1a;
  transform: rotate(1.5deg);
}

.data-card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 13px; }
.data-card-head strong { font-size: 14px; }
.read-only { border-radius: 999px; padding: 5px 8px; background: #72d89b16; color: var(--green); font-size: 10px; font-weight: 850; letter-spacing: .06em; text-transform: uppercase; }
.data-list { display: grid; gap: 8px; }

.data-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  border: 1px solid #433538;
  border-radius: 12px;
  padding: 10px;
  background: #ffffff06;
}

.data-icon { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; background: #e3261e1a; color: #ff756d; font-size: 11px; font-weight: 900; }
.data-label { overflow: hidden; font-size: 12px; font-weight: 780; text-overflow: ellipsis; white-space: nowrap; }
.data-state { color: var(--muted); font-size: 10px; }

.trust-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 22px; }
.trust-item { border-top: 1px solid #563c40; padding-top: 10px; }
.trust-item strong { display: block; margin-bottom: 4px; color: var(--text); font-size: 11px; }
.trust-item span { display: block; color: var(--muted); font-size: 10px; line-height: 1.4; }

.footer {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  border-top: 1px solid var(--line-soft);
  padding: 14px 24px;
  background: #171314;
  color: #8f7e81;
  font-size: 10px;
  line-height: 1.45;
}

.disconnect-copy { max-width: 550px; }
.disconnect-list { display: grid; gap: 10px; margin: 22px 0; }
.disconnect-item { display: flex; gap: 10px; color: var(--muted-strong); font-size: 13px; line-height: 1.45; }
.disconnect-item::before { flex: 0 0 auto; color: var(--red-bright); font-weight: 900; content: "—"; }

@media (max-width: 880px) {
  .page { padding: 14px; }
  .shell { border-radius: 22px; }
  .layout { grid-template-columns: 1fr; }
  .primary-panel { padding: 42px 28px; }
  .showcase { border-top: 1px solid var(--line-soft); border-left: 0; padding: 42px 28px; }
  .showcase-content { width: 100%; }
  .data-card { transform: none; }
}

@media (max-width: 560px) {
  .page { display: block; padding: 0; }
  .shell { min-height: 100vh; border: 0; border-radius: 0; }
  .topbar { padding: 14px 18px; }
  .unofficial { max-width: 118px; padding: 6px 8px; font-size: 9px; text-align: center; }
  .primary-panel { padding: 36px 20px; }
  h1 { font-size: 44px; }
  .flow-panel { padding: 18px; }
  .showcase { padding: 36px 20px; }
  .trust-grid { grid-template-columns: 1fr; }
  .footer { flex-direction: column; padding: 14px 18px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
}
"""


CONNECT_CONTENT = r"""
<section class="primary-panel" aria-labelledby="page-title">
  <p class="eyebrow">Conexión local segura</p>
  <h1 id="page-title">Conecta <em>tu liga.</em></h1>
  <p class="lead">Accede con tu cuenta de Biwenger para consultar plantilla, presupuesto y mercado desde Claude. Este MCP no puede pujar, vender ni cambiar tu alineación.</p>
  <div class="local-note">
    <span class="local-note-icon" aria-hidden="true">✓</span>
    <span>Esta página se ejecuta localmente en tu ordenador. La contraseña se utiliza para iniciar sesión en Biwenger y se descarta inmediatamente.</span>
  </div>

  <form id="login" class="flow-panel" novalidate>
    <label class="field">
      <span class="field-label">Correo de Biwenger</span>
      <span class="input-wrap">
        <span class="input-icon" aria-hidden="true">@</span>
        <input name="email" type="email" maxlength="320" required autocomplete="username" inputmode="email" spellcheck="false" placeholder="tu@correo.com">
      </span>
    </label>
    <label class="field">
      <span class="field-label">Contraseña propia de Biwenger</span>
      <span class="input-wrap">
        <span class="input-icon" aria-hidden="true">••</span>
        <input name="password" type="password" maxlength="1024" required autocomplete="current-password" placeholder="Tu contraseña">
      </span>
    </label>
    <button class="button button-primary" type="submit"><span>Conectar cuenta</span><span class="arrow" aria-hidden="true">→</span></button>
    <p class="account-help">¿Te registraste con Google, Apple o Facebook? No introduzcas aquí esas contraseñas. <a href="https://www.biwenger.com/faq/cuentas-contrasenas-combinar-cuentas/" target="_blank" rel="noreferrer">Configura una contraseña propia en la ayuda oficial de Biwenger</a>.</p>
  </form>

  <section id="leagues" class="flow-panel" aria-labelledby="league-title" hidden>
    <header class="section-head">
      <small>Paso 2 de 2</small>
      <h2 id="league-title">Elige tu liga</h2>
      <p>Mostramos las ligas compatibles y su sistema de puntuación. La selección se puede cambiar más adelante.</p>
    </header>
    <div id="choices" class="choices" role="group" aria-label="Ligas compatibles"></div>
    <button id="change-account" class="text-button" type="button">Usar otra cuenta</button>
  </section>

  <section id="success" class="flow-panel success-panel" aria-labelledby="success-title" hidden>
    <div class="success-mark" aria-hidden="true">✓</div>
    <h2 id="success-title">Cuenta conectada</h2>
    <p>La sesión se ha guardado en el almacenamiento seguro del sistema. La contraseña no se conserva.</p>
    <div class="next-steps" aria-label="Siguientes pasos">
      <div class="next-step"><span>1</span>Cierra completamente Claude Desktop.</div>
      <div class="next-step"><span>2</span>Vuelve a abrirlo para reiniciar la extensión.</div>
      <div class="next-step"><span>3</span>Pregunta por el contexto de tu liga.</div>
    </div>
  </section>

  <p id="status" class="status" role="status" aria-live="polite" hidden></p>
</section>
"""


DISCONNECT_CONTENT = r"""
<section class="primary-panel" aria-labelledby="page-title">
  <p class="eyebrow">Control de la conexión</p>
  <h1 id="page-title">Desconecta <em>con control.</em></h1>
  <p class="lead disconnect-copy">Esta acción elimina la sesión de Biwenger del almacenamiento seguro del sistema y borra la configuración local de la extensión.</p>
  <div class="flow-panel" id="disconnect-panel">
    <div class="disconnect-list">
      <div class="disconnect-item">No modifica tu equipo, el mercado ni la alineación.</div>
      <div class="disconnect-item">No elimina tu cuenta de Biwenger.</div>
      <div class="disconnect-item">Podrás volver a conectarla cuando quieras.</div>
    </div>
    <button id="disconnect" class="button button-danger" type="button">Desconectar cuenta</button>
  </div>
  <section id="disconnect-success" class="flow-panel success-panel" aria-labelledby="success-title" hidden>
    <div class="success-mark" aria-hidden="true">✓</div>
    <h2 id="success-title">Cuenta desconectada</h2>
    <p>Cierra completamente Claude Desktop y vuelve a abrirlo para reiniciar la extensión sin la sesión anterior.</p>
  </section>
  <p id="status" class="status" role="status" aria-live="polite" hidden></p>
</section>
"""


SHOWCASE = r"""
<aside class="showcase" aria-label="Características de seguridad">
  <div class="showcase-content">
    <span class="showcase-kicker">Tu asistente de liga</span>
    <h2>Datos claros.<br>Decisiones tuyas.</h2>
    <p class="showcase-copy">Consulta la información que ya ves en Biwenger y úsala para analizar tu equipo. Las acciones deportivas permanecen bloqueadas.</p>
    <div class="data-card" aria-label="Capacidades de solo lectura">
      <div class="data-card-head"><strong>Biwenger MCP</strong><span class="read-only">Solo lectura</span></div>
      <div class="data-list">
        <div class="data-row"><span class="data-icon">XI</span><span class="data-label">Plantilla y alineación</span><span class="data-state">Consultar</span></div>
        <div class="data-row"><span class="data-icon">€</span><span class="data-label">Presupuesto y mercado</span><span class="data-state">Analizar</span></div>
        <div class="data-row"><span class="data-icon">↗</span><span class="data-label">Jugadores e históricos</span><span class="data-state">Comparar</span></div>
      </div>
    </div>
    <div class="trust-grid">
      <div class="trust-item"><strong>Local</strong><span>Se abre en 127.0.0.1</span></div>
      <div class="trust-item"><strong>Efímero</strong><span>Caduca en diez minutos</span></div>
      <div class="trust-item"><strong>Privado</strong><span>La contraseña no se guarda</span></div>
    </div>
  </div>
</aside>
"""


CONNECT_SCRIPT = r"""
const nonce = __NONCE__;
const form = document.querySelector('#login');
const status = document.querySelector('#status');
const leagues = document.querySelector('#leagues');
const choices = document.querySelector('#choices');
const success = document.querySelector('#success');
const changeAccount = document.querySelector('#change-account');

const formBody = data => new URLSearchParams({...data, nonce});
const setStatus = (message, tone = 'info') => {
  status.textContent = message;
  status.dataset.tone = tone;
  status.hidden = !message;
};
const send = async (path, data) => {
  const response = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: formBody(data)
  });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error?.message || 'No se pudo completar');
  return value;
};
const setChoicesDisabled = disabled => {
  for (const button of choices.querySelectorAll('button')) button.disabled = disabled;
};

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const submit = form.querySelector('[type="submit"]');
  const values = new FormData(form);
  submit.disabled = true;
  submit.setAttribute('aria-busy', 'true');
  setStatus('Comprobando la cuenta…');
  try {
    const value = await send('/api/login/' + nonce, {
      email: values.get('email'),
      password: values.get('password')
    });
    form.reset();
    choices.replaceChildren();
    for (const league of value.leagues) {
      const button = document.createElement('button');
      const name = document.createElement('span');
      const score = document.createElement('span');
      const meta = document.createElement('span');
      button.type = 'button';
      button.className = 'league-choice';
      name.className = 'league-name';
      score.className = 'league-score';
      meta.className = 'league-meta';
      name.textContent = league.name;
      score.textContent = league.score_name;
      meta.textContent = 'LaLiga · Fichajes Clásica';
      button.append(name, score, meta);
      button.addEventListener('click', async () => {
        setChoicesDisabled(true);
        setStatus('Verificando la liga…');
        try {
          await send('/api/select/' + nonce, {league_id: String(league.league_id)});
          leagues.hidden = true;
          success.hidden = false;
          setStatus('Conexión completada.', 'success');
        } catch (error) {
          setChoicesDisabled(false);
          setStatus(error.message, 'error');
        }
      });
      choices.appendChild(button);
    }
    form.hidden = true;
    leagues.hidden = false;
    setStatus('Cuenta verificada. Elige la liga que quieres usar.', 'success');
    leagues.querySelector('button')?.focus();
  } catch (error) {
    form.querySelector('[name="password"]').value = '';
    setStatus(error.message, 'error');
  } finally {
    submit.disabled = false;
    submit.removeAttribute('aria-busy');
  }
});

changeAccount.addEventListener('click', () => {
  leagues.hidden = true;
  form.hidden = false;
  setStatus('');
  form.querySelector('[name="email"]').focus();
});
"""


DISCONNECT_SCRIPT = r"""
const nonce = __NONCE__;
const status = document.querySelector('#status');
const panel = document.querySelector('#disconnect-panel');
const success = document.querySelector('#disconnect-success');
const button = document.querySelector('#disconnect');
const setStatus = (message, tone = 'info') => {
  status.textContent = message;
  status.dataset.tone = tone;
  status.hidden = !message;
};

button.addEventListener('click', async () => {
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  setStatus('Desconectando la cuenta…');
  try {
    const response = await fetch('/api/disconnect/' + nonce, {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({nonce, confirm: 'disconnect'})
    });
    const value = await response.json();
    if (!response.ok) throw new Error(value.error?.message || 'No se pudo desconectar');
    panel.hidden = true;
    success.hidden = false;
    setStatus('Sesión local eliminada.', 'success');
  } catch (error) {
    button.disabled = false;
    button.removeAttribute('aria-busy');
    setStatus(error.message, 'error');
  }
});
"""


def render_page(mode: str, nonce: str, script_nonce: str) -> str:
    """Genera una página completa sin interpolar datos de la cuenta."""
    if mode == "connect":
        title = "Conectar Biwenger MCP"
        content = CONNECT_CONTENT
        script = CONNECT_SCRIPT
    elif mode == "disconnect":
        title = "Desconectar Biwenger MCP"
        content = DISCONNECT_CONTENT
        script = DISCONNECT_SCRIPT
    else:
        raise ValueError("invalid wizard mode")
    script = script.replace("__NONCE__", json.dumps(nonce))
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>{safe_title}</title>
  <style>{STYLES}</style>
</head>
<body>
  <div class="page">
    <span class="orb orb-one" aria-hidden="true"></span>
    <span class="orb orb-two" aria-hidden="true"></span>
    <main class="shell">
      <header class="topbar">
        <span class="brand-mark" aria-hidden="true">M</span>
        <span class="brand-copy"><strong>Biwenger MCP</strong><span>Asistente de conexión</span></span>
        <span class="unofficial">Proyecto no oficial</span>
      </header>
      <div class="layout">{content}{SHOWCASE}</div>
      <footer class="footer">
        <span>Proyecto independiente, no afiliado, patrocinado ni respaldado por Biwenger o Diario AS.</span>
        <span>Conexión local · Enlace válido durante diez minutos</span>
      </footer>
    </main>
  </div>
  <script nonce="{html.escape(script_nonce)}">{script}</script>
</body>
</html>"""

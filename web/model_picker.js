import { api } from "/scripts/api.js";

let dialog, resolveSelection, controller, requestId = 0, previousFocus;
let source = "public", page = 1, hasNext = false;
const $ = selector => dialog.querySelector(selector);

async function jsonRequest(url, options) {
  const response = await api.fetchApi(url, options);
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function close(value = null) {
  ++requestId;
  controller?.abort();
  $('[data-credential]').value = "";
  dialog.close();
  resolveSelection?.(value);
  resolveSelection = null;
  previousFocus?.focus?.();
}

function createPicker() {
  if (dialog) return;
  const style = document.createElement("style");
  style.textContent = `
.fast-rh-catalog{color-scheme:dark;box-sizing:border-box;width:min(1080px,94vw);height:min(800px,90vh);max-width:94vw;max-height:90vh;padding:24px;background:#0b0b0d;color:#eee;border:1px solid #303034;border-radius:8px;font:14px system-ui;overflow:hidden}
.fast-rh-catalog[open]{display:flex;flex-direction:column;gap:18px}.fast-rh-catalog::backdrop{background:#000b}
.fast-rh-catalog *{box-sizing:border-box}.fast-rh-catalog button{cursor:pointer;border:1px solid #333;background:#242426;color:#eee;padding:10px 16px;border-radius:3px;font:inherit}.fast-rh-catalog button:hover{border-color:#c4ff00}.fast-rh-catalog button:disabled{opacity:.4;cursor:default}
.fast-rh-catalog button:focus-visible,.fast-rh-catalog select:focus-visible{outline:2px solid #c4ff00;outline-offset:2px}
.fast-rh-head,.fast-rh-search,.fast-rh-footer,.fast-rh-login-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.fast-rh-head nav{display:flex;gap:12px;flex:1}.fast-rh-head nav button{background:none;border:0;border-bottom:2px solid transparent;color:#939398;padding:10px 0;margin-right:16px}.fast-rh-head nav button[aria-pressed=true]{color:#c4ff00;border-bottom-color:#c4ff00}
.fast-rh-catalog input,.fast-rh-catalog select{background:#19191c;color:#eee;border:1px solid #36363a;padding:12px;font:inherit;min-width:0}.fast-rh-search input{flex:1}.fast-rh-catalog .fast-rh-primary{background:#c4ff00;color:#101200;border-color:#c4ff00}
.fast-rh-auth{color:#a7a7ae;font-size:12px}.fast-rh-auth[data-valid=true]{color:#2bcac3}.fast-rh-auth[data-valid=false]{color:#f1a867}.fast-rh-status{color:#a7a7ae;min-height:20px}.fast-rh-grid{flex:1;min-height:0;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));align-content:start;grid-auto-rows:max-content;gap:12px;padding:2px}
.fast-rh-card{position:relative;min-width:0;background:#202024;border:1px solid #35353a;overflow:hidden;border-radius:3px}.fast-rh-card:hover{border-color:#c4ff00}.fast-rh-catalog .fast-rh-pick{display:block;position:relative;width:100%;height:300px;padding:0;border:0;text-align:left;background:linear-gradient(135deg,#292932,#131319)}.fast-rh-pick img{width:100%;height:100%;object-fit:cover}.fast-rh-card-labels{position:absolute;top:10px;left:10px;right:10px;display:flex;justify-content:space-between;gap:8px}.fast-rh-card-labels span{padding:4px 7px;background:#0009;font-size:11px;max-width:75%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fast-rh-card-info{position:absolute;bottom:0;left:0;right:0;padding:44px 10px 12px;background:linear-gradient(transparent,#000e);display:grid;gap:8px}.fast-rh-card-title,.fast-rh-card-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fast-rh-card-name{font-size:12px;color:#bdbdc4}.fast-rh-card-bottom{display:flex;align-items:center;gap:6px;padding:8px}.fast-rh-card-bottom select{flex:1;width:0;padding:5px;font-size:12px}.fast-rh-collected{color:#2bcac3;font-size:12px}.fast-rh-footer{justify-content:flex-end}.fast-rh-footer small{margin-right:auto;color:#919199}
.fast-rh-login{background:#19191c;border:1px solid #38383d;padding:16px}.fast-rh-login[hidden]{display:none}.fast-rh-login p{margin:0 0 12px;color:#bdbdc4;line-height:1.6}.fast-rh-login input{flex:1}.fast-rh-login-message{margin-top:10px;color:#c4ff00}
@media(max-width:600px){.fast-rh-catalog{padding:12px;gap:10px}.fast-rh-head nav{gap:6px}.fast-rh-auth{max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fast-rh-head nav button{margin-right:6px}.fast-rh-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.fast-rh-catalog .fast-rh-pick{height:240px}}
`;
  document.head.append(style);
  dialog = document.createElement("dialog");
  dialog.className = "fast-rh-catalog";
  dialog.setAttribute("aria-label", "选择 RunningHub LoRA 模型");
  dialog.innerHTML = `
    <header class="fast-rh-head"><nav aria-label="模型来源"><button data-source="public">公共模型</button><button data-source="uploaded">我上传的</button><button data-source="favorites">我的收藏</button></nav><span class="fast-rh-auth" data-auth role="status" aria-live="polite">检查登录…</span><button data-login>登录设置</button><button data-close aria-label="关闭">✕</button></header>
    <section class="fast-rh-login" hidden><p>先在 RunningHub 网站登录，再从浏览器开发者工具的 Cookie 中复制 Rh-Accesstoken，粘贴到这里。也支持完整 Cookie 或 Bearer 值。登录只保存在本地服务端，不写入工作流。过期后重新导入即可。</p><div class="fast-rh-login-actions"><select data-site aria-label="RunningHub 站点"><option value="https://www.runninghub.ai">国际站 .ai</option><option value="https://www.runninghub.cn">国内站 .cn</option></select><input data-credential type="password" autocomplete="off" placeholder="粘贴 Rh-Accesstoken 或 Cookie" aria-label="登录令牌"><button data-save class="fast-rh-primary">保存登录</button><button data-clear>清除登录</button></div><div class="fast-rh-login-message" role="status"></div></section>
    <form class="fast-rh-search"><input data-query placeholder="搜索模型" aria-label="搜索模型" maxlength="200"><button class="fast-rh-primary" type="submit">搜索</button><button data-refresh type="button">刷新</button></form>
    <div class="fast-rh-status" role="status" aria-live="polite"></div><div class="fast-rh-grid"></div>
    <footer class="fast-rh-footer"><small>点击封面选择模型 · 多版本可在卡片下方切换</small><button data-prev>上一页</button><span data-page></span><button data-next>下一页</button></footer>`;
  document.body.append(dialog);
  $('[data-close]').onclick = () => close();
  dialog.addEventListener("cancel", event => { event.preventDefault(); close(); });
  dialog.addEventListener("click", event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) close(); } });
  dialog.querySelectorAll('[data-source]').forEach(button => button.onclick = () => { source = button.dataset.source; load(1); });
  $('.fast-rh-search').onsubmit = event => { event.preventDefault(); load(1); };
  $('[data-refresh]').onclick = () => load(page);
  $('[data-prev]').onclick = () => load(page - 1);
  $('[data-next]').onclick = () => load(page + 1);
  $('[data-login]').onclick = () => { $('.fast-rh-login').hidden = !$('.fast-rh-login').hidden; if (!$('.fast-rh-login').hidden) $('[data-credential]').focus(); };
  $('[data-save]').onclick = () => changeSession(false);
  $('[data-clear]').onclick = () => changeSession(true);
}

async function changeSession(clear) {
  const message = $('.fast-rh-login-message');
  $('[data-save]').disabled = $('[data-clear]').disabled = true;
  ++requestId;
  controller?.abort();
  $('.fast-rh-grid').replaceChildren();
  try {
    await jsonRequest('/fast-rh/session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(clear ? { clear: true } : { site: $('[data-site]').value, credential: $('[data-credential]').value }) });
    $('[data-credential]').value = '';
    message.textContent = clear ? '已清除本地登录信息' : '已保存，正在检查登录状态…';
    await refreshAuthStatus();
    await load(1);
  } catch (error) { message.textContent = error.message; }
  finally { $('[data-save]').disabled = $('[data-clear]').disabled = false; }
}

function renderCard(item) {
  const card = document.createElement('article');
  card.className = 'fast-rh-card';
  card.innerHTML = `<button class="fast-rh-pick"><img loading="lazy" referrerpolicy="no-referrer" alt=""><div class="fast-rh-card-labels"><span>LORA</span><span data-base></span></div><div class="fast-rh-card-info"><strong class="fast-rh-card-title"></strong><span class="fast-rh-card-name"></span></div></button><div class="fast-rh-card-bottom"><select aria-label="模型版本"></select><span class="fast-rh-collected"></span></div>`;
  const pick = card.querySelector('button'), select = card.querySelector('select'), img = card.querySelector('img');
  card.querySelector('.fast-rh-card-title').textContent = item.title;
  card.querySelector('.fast-rh-collected').textContent = item.collected ? '★ 已收藏' : '';
  item.versions.forEach((v, i) => { const option = document.createElement('option'); option.value = i; option.textContent = v.version; select.append(option); });
  const update = () => {
    const v = item.versions[Number(select.value)];
    const name = v?.model || '暂无可用版本';
    card.querySelector('.fast-rh-card-name').textContent = name;
    card.querySelector('[data-base]').textContent = v?.base_model || '—';
    pick.title = `${item.title}\n${name}`;
    pick.setAttribute('aria-label', `选择 ${item.title} ${v?.version || ''}`);
    pick.disabled = !v;
    const image = v?.image || item.image;
    img.hidden = !image;
    if (image) img.src = image; else img.removeAttribute('src');
  };
  img.onerror = () => { img.hidden = true; };
  select.onchange = update;
  select.disabled = !item.versions.length;
  pick.onclick = () => close(item.versions[Number(select.value)].model);
  update();
  return card;
}

async function load(nextPage = 1) {
  const id = ++requestId;
  controller?.abort();
  controller = new AbortController();
  page = Math.max(1, nextPage);
  dialog.querySelectorAll('[data-source]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.source === source)));
  $('[data-prev]').disabled = $('[data-next]').disabled = true;
  $('[data-page]').textContent = `第 ${page} 页`;
  $('.fast-rh-status').textContent = '正在加载 RunningHub 模型…';
  $('.fast-rh-grid').replaceChildren();
  try {
    const params = new URLSearchParams({ source, page: String(page), q: $('[data-query]').value.trim() });
    const data = await jsonRequest(`/fast-rh/resources?${params}`, { signal: controller.signal });
    if (id !== requestId || !dialog.open) return;
    hasNext = data.has_next;
    $('.fast-rh-grid').replaceChildren(...data.items.map(renderCard));
    $('.fast-rh-grid').scrollTop = 0;
    $('.fast-rh-status').textContent = data.items.length ? `共 ${data.total.toLocaleString()} 个模型 · 本页 ${data.items.length} 个` : '没有匹配的模型，试试其他关键词或分类';
  } catch (error) {
    if (id !== requestId || error.name === 'AbortError') return;
    hasNext = false;
    $('.fast-rh-status').textContent = `加载失败：${error.message}`;
  } finally {
    if (id === requestId) { $('[data-prev]').disabled = page <= 1; $('[data-next]').disabled = !hasNext; }
  }
}

export function chooseLora() {
  createPicker();
  if (resolveSelection) close();
  previousFocus = document.activeElement;
  const result = new Promise(resolve => { resolveSelection = resolve; });
  dialog.showModal();
  load(1);
  $('[data-query]').focus();
  refreshAuthStatus().then(data => {
    if (!dialog.open || !data) return;
    if (data.site) $('[data-site]').value = data.site;
    $('.fast-rh-login').hidden = data.authenticated;
  });
  return result;
}

async function refreshAuthStatus() {
  const badge = $('[data-auth]');
  badge.textContent = '检查登录…';
  badge.removeAttribute('data-valid');
  try {
    const data = await jsonRequest('/fast-rh/session');
    if (!dialog.open) return data;
    if (data.site) $('[data-site]').value = data.site;
    if (data.authenticated && Number.isFinite(Number(data.token_expires_at))) {
      const expiration = new Date(Number(data.token_expires_at));
      badge.textContent = `令牌有效至 ${expiration.toLocaleString()}`;
      badge.dataset.valid = 'true';
      return data;
    }
    badge.textContent = data.configured ? '登录已过期' : '尚未登录';
    badge.dataset.valid = 'false';
    if (data.error) $('.fast-rh-login-message').textContent = data.error;
    return data;
  } catch (error) {
    if (dialog.open) {
      badge.textContent = '登录检查失败';
      badge.dataset.valid = 'false';
      $('.fast-rh-login-message').textContent = error.message;
    }
  }
}

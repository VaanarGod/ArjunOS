import Foundation

/// JavaScript the agent runs inside the page. It runs in its OWN content world (WKContentWorld "ArjunComputer"): it sees the same DOM as the page,
/// but not the page's variables, and the page cannot see or change this code or the built-in objects it uses. A hostile page therefore cannot
/// make a password field look harmless or rewrite what the agent reads; it can only lie in the text it shows, which the bridge treats as untrusted.
enum ComputerScripts {
    /// `run(op, arg)` returns a JSON string. Ops: scan, act.
    static let prelude = #"""
    (function(){
      if (!window.__arjunC) window.__arjunC = {gen: 0, els: []};
      const S = window.__arjunC;
      const norm = s => (s || '').replace(/\s+/g, ' ').trim();
      const vw = () => window.innerWidth, vh = () => window.innerHeight;
      const SEL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox],[role=radio],[role=switch],[role=option],[role=combobox],[contenteditable=""],[contenteditable=true],[tabindex]:not([tabindex="-1"])';
      const SECRET_AC = /(current-password|new-password|one-time-code|cc-number|cc-csc|cc-exp)/;
      function visible(el, r) {
        if (r.width < 3 || r.height < 3) return false;
        if (r.bottom < 0 || r.right < 0 || r.top > vh() || r.left > vw()) return false;
        const cs = getComputedStyle(el);
        return !(cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0);
      }
      function isSecure(el) {
        return el.tagName === 'INPUT' && (el.type === 'password' || SECRET_AC.test((el.getAttribute('autocomplete') || '').toLowerCase()));
      }
      function isEditable(el) {
        if (!el) return false;
        if (el.isContentEditable) return true;
        if (el.tagName === 'TEXTAREA') return !el.readOnly;
        if (el.tagName !== 'INPUT') return false;
        return !['checkbox','radio','button','submit','reset','image','file','range','color','hidden'].includes((el.type || 'text').toLowerCase()) && !el.readOnly;
      }
      function labelOf(el) {
        const aria = el.getAttribute('aria-label'); if (norm(aria)) return norm(aria).slice(0, 90);
        const lb = el.getAttribute('aria-labelledby');
        if (lb) { const t = norm(lb.split(/\s+/).map(id => { const n = document.getElementById(id); return n ? n.textContent : ''; }).join(' ')); if (t) return t.slice(0, 90); }
        if (el.labels && el.labels.length) { const t = norm(el.labels[0].textContent); if (t) return t.slice(0, 90); }
        if (el.tagName === 'INPUT') {
          const t = (el.type || 'text').toLowerCase();
          if (['button','submit','reset'].includes(t)) return norm(el.value).slice(0, 90) || t;
          return norm(el.placeholder).slice(0, 90) || norm(el.title).slice(0, 90) || el.name || t;
        }
        if (el.tagName === 'TEXTAREA') return norm(el.placeholder).slice(0, 90) || norm(el.title).slice(0, 90) || el.name || 'text area';
        const txt = norm(el.innerText || el.textContent); if (txt) return txt.slice(0, 90);
        const img = el.querySelector && el.querySelector('img[alt]');
        return norm(el.getAttribute('title')).slice(0, 90) || (img ? norm(img.alt).slice(0, 90) : '');
      }
      function roleOf(el) {
        const r = el.getAttribute('role'), tag = el.tagName;
        if (tag === 'A') return 'link';
        if (tag === 'BUTTON' || r === 'button') return 'button';
        if (tag === 'SELECT') return 'pop up button';
        if (tag === 'TEXTAREA') return 'text field';
        if (tag === 'INPUT') {
          const t = (el.type || 'text').toLowerCase();
          if (t === 'checkbox') return 'checkbox'; if (t === 'radio') return 'radio button';
          if (['button','submit','reset','image'].includes(t)) return 'button';
          return 'text field';
        }
        if (r) return r === 'menuitem' ? 'menu item' : r;
        return el.isContentEditable ? 'text field' : 'element';
      }
      function scan(max) {
        const out = []; S.els = []; S.gen++;
        for (const el of document.querySelectorAll(SEL)) {
          if (out.length >= max) break;
          if (el.disabled) continue;
          const r = el.getBoundingClientRect(); if (!visible(el, r)) continue;
          const cx = Math.min(Math.max(r.left + r.width / 2, 0), vw() - 1), cy = Math.min(Math.max(r.top + r.height / 2, 0), vh() - 1);
          const top = document.elementFromPoint(cx, cy);                       // something else on top (a modal, a banner)? then it cannot be clicked
          if (top && top !== el && !el.contains(top) && !top.contains(el)) continue;
          const secure = isSecure(el), i = S.els.length; S.els.push(el);
          const isCheck = el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio');
          out.push({i, role: roleOf(el), label: labelOf(el), x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height),
                    secure, editable: isEditable(el), value: (!secure && typeof el.value === 'string') ? el.value.slice(0, 60) : '', checked: isCheck ? !!el.checked : null});
        }
        const a = document.activeElement;
        return {gen: S.gen, elements: out, labels: out.map(e => e.label.toLowerCase()).filter(Boolean),
                focused: a && a !== document.body ? labelOf(a) : '', has_secure: out.some(e => e.secure),
                url: location.href, title: document.title, vw: vw(), vh: vh(), scroll_y: Math.round(window.scrollY),
                loading: document.readyState !== 'complete'};
      }
      function pick(a) {
        if (a.element != null) { if (a.gen !== S.gen) return {err: 'stale'}; return {el: S.els[a.element]}; }
        if (a.x != null) return {el: document.elementFromPoint(a.x, a.y)};
        return {el: document.activeElement};
      }
      function submit(el) {
        const form = el.form || (el.closest && el.closest('form'));
        const fire = t => el.dispatchEvent(new KeyboardEvent(t, {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true}));
        const ok = fire('keydown'); fire('keypress'); fire('keyup');           // many search boxes listen for Enter itself, not for a form submit
        if (ok && form) { if (form.requestSubmit) form.requestSubmit(); else form.submit(); }
      }
      function focusNext(back) {
        const list = Array.from(document.querySelectorAll(SEL)).filter(e => !e.disabled && visible(e, e.getBoundingClientRect()));
        if (!list.length) return;
        const i = list.indexOf(document.activeElement);
        list[(i + (back ? -1 : 1) + list.length) % list.length].focus();
      }
      const KEYS = {enter:['Enter',13], tab:['Tab',9], esc:['Escape',27], space:[' ',32], backspace:['Backspace',8], delete:['Delete',46], up:['ArrowUp',38],
                    down:['ArrowDown',40], left:['ArrowLeft',37], right:['ArrowRight',39], home:['Home',36], end:['End',35], pageup:['PageUp',33], pagedown:['PageDown',34]};
      function act(a) {
        if (a.kind === 'click') {
          const f = pick(a); if (f.err) return {ok: false, code: 'stale', error: 'The page changed since I looked. Look again.'};
          const el = f.el; if (!el) return {ok: false, error: 'Nothing is at that spot.'};
          el.scrollIntoView({block: 'center', inline: 'center'});
          const r = el.getBoundingClientRect(), o = {bubbles: true, cancelable: true, view: window, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, button: a.button === 'right' ? 2 : 0};
          if (el.focus) el.focus({preventScroll: true});
          for (const t of ['pointerover','mouseover','pointerdown','mousedown','pointerup','mouseup']) el.dispatchEvent(new (t.startsWith('pointer') ? PointerEvent : MouseEvent)(t, o));
          if (a.button === 'right') { el.dispatchEvent(new MouseEvent('contextmenu', o)); return {ok: true, note: 'right-clicked'}; }
          el.click();                                                          // runs the page's handlers and the default action (follow the link, toggle, submit)
          if (a.double) { el.click(); el.dispatchEvent(new MouseEvent('dblclick', o)); }
          return {ok: true, note: 'clicked'};
        }
        if (a.kind === 'type') {
          const targeted = a.element != null || a.x != null;
          const f = pick(a); if (f.err) return {ok: false, code: 'stale', error: 'The page changed since I looked. Look again.'};
          let el = f.el;
          if (el && !isEditable(el) && el.querySelector) { const inner = el.querySelector('input,textarea,[contenteditable]'); if (inner) el = inner; }
          if (!el || !isEditable(el)) return {ok: false, error: 'That is not a text field.'};
          if (isSecure(el)) return {ok: false, code: 'secure', error: 'Password and payment fields are never typed into by the assistant.'};
          el.scrollIntoView({block: 'center'}); el.focus();
          if (targeted) {                                                      // with a target the field's text is REPLACED; without one it types at the cursor
            if (el.isContentEditable) { document.execCommand('selectAll'); document.execCommand('insertText', false, a.text); }
            else {
              const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, a.text);   // the native setter, so frameworks such as React notice the input event
              el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));
            }
          } else document.execCommand('insertText', false, a.text);
          if (a.submit) submit(el);
          return {ok: true, note: 'typed'};
        }
        if (a.kind === 'key') {
          const parts = String(a.keys).split('+'), main = parts[parts.length - 1], mods = parts.slice(0, -1);
          if (mods.includes('cmd') || mods.includes('ctrl')) return {ok: false, code: 'unsupported', error: 'Shortcuts with cmd or ctrl cannot be sent to a web page. Click the control, or use navigate.'};
          const t = document.activeElement || document.body;
          if (main === 'enter' && isEditable(t)) { submit(t); return {ok: true, note: 'enter'}; }
          if (main === 'tab') { focusNext(mods.includes('shift')); return {ok: true, note: 'tab'}; }
          const k = KEYS[main] || [main, main.toUpperCase().charCodeAt(0)];
          const init = {key: k[0], code: k[0], keyCode: k[1], which: k[1], bubbles: true, cancelable: true, shiftKey: mods.includes('shift'), altKey: mods.includes('opt')};
          const ok = t.dispatchEvent(new KeyboardEvent('keydown', init)); t.dispatchEvent(new KeyboardEvent('keypress', init)); t.dispatchEvent(new KeyboardEvent('keyup', init));
          if (ok) { const step = vh() * 0.8; if (main === 'down' || main === 'pagedown' || main === 'space') window.scrollBy(0, step); else if (main === 'up' || main === 'pageup') window.scrollBy(0, -step); else if (main === 'home') window.scrollTo(0, 0); else if (main === 'end') window.scrollTo(0, document.body.scrollHeight); }
          return {ok: true, note: main};
        }
        if (a.kind === 'scroll') {
          const dy = (a.direction === 'down' ? 1 : a.direction === 'up' ? -1 : 0) * (a.amount || 3) * vh() * 0.25, dx = (a.direction === 'right' ? 1 : a.direction === 'left' ? -1 : 0) * (a.amount || 3) * vw() * 0.25;
          const f = a.element != null ? pick(a) : {};
          if (f.err) return {ok: false, code: 'stale', error: 'The page changed since I looked. Look again.'};
          (f.el && f.el.scrollBy ? f.el : window).scrollBy({top: dy, left: dx, behavior: 'instant'});
          return {ok: true, note: 'scrolled'};
        }
        return {ok: false, error: 'Unsupported action in the browser: ' + a.kind};
      }
      window.__arjunRun = (op, arg) => JSON.stringify(op === 'scan' ? scan(arg.max || 120) : act(arg));
    })();
    """#

    static func source(op: String, argJSON: String) -> String {
        let opJSON = (try? String(data: JSONEncoder().encode(op), encoding: .utf8)) ?? "\"scan\""
        return prelude + "; window.__arjunRun(\(opJSON), \(argJSON));"
    }
}
